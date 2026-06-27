"""Autenticación y autorización por rol para el backend.

Implementa T7 paso 5 de docs/roles-permisos.md: una dependencia `require_role`
que verifica el JWT de Supabase y obtiene `user_id`, `company_id` y `role`
DESDE EL SERVIDOR (nunca del body del cliente).

IMPORTANTE — pendiente de cableado (depende de R1 del doc de seguridad):
El backend usa `service_role`, que ignora la RLS. Mientras este módulo NO se
inyecte en los routers, los endpoints siguen siendo públicos. Cablear
`Depends(require_role(...))` en `/documents/upload` (y futuros endpoints de
empresa) requiere además que el frontend envíe el header
`Authorization: Bearer <access_token>` (hoy el upload no lo manda). El widget de
chat (`/chat`) es público por diseño y NO debe llevar este guard.
"""

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from app.config import supabase

# Jerarquía de roles (owner ⊇ admin ⊇ member ⊇ viewer).
ROLE_ORDER = {"viewer": 0, "member": 1, "admin": 2, "owner": 3}


@dataclass
class CurrentUser:
    id: str
    company_id: str | None
    role: str


def _extract_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el token de autenticación.",
        )
    return authorization.split(" ", 1)[1].strip()


async def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    """Valida el JWT de Supabase y resuelve el rol/empresa del usuario en el servidor."""
    token = _extract_token(authorization)

    # Verifica el token contra Supabase Auth (no confía en su contenido sin validar).
    auth_response = supabase.auth.get_user(token)
    user = getattr(auth_response, "user", None)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
        )

    # El rol y la empresa se leen de public.users, jamás del cliente.
    profile = (
        supabase.table("users")
        .select("company_id, role")
        .eq("id", user.id)
        .single()
        .execute()
    )
    data = profile.data or {}
    return CurrentUser(
        id=user.id,
        company_id=data.get("company_id"),
        role=data.get("role", "viewer"),
    )


def require_role(*allowed_roles: str):
    """Dependencia que exige que el rol del usuario esté entre `allowed_roles`.

    Uso (una vez cableada la auth):
        @router.post("/upload")
        async def upload(..., user: CurrentUser = Depends(require_role("owner", "admin", "member"))):
    """
    allowed = set(allowed_roles)

    async def _guard(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed:
            # Error genérico al cliente; el detalle del motivo va al log del servidor.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta acción.",
            )
        return user

    return _guard
