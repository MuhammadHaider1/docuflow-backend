from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.rbac import Permission, Role
from src.repositories.rbac import RBACRepository


async def seed_system_roles(db: AsyncSession) -> None:
    ROLES_TO_SEED = [
        "Super Admin",
        "Platform Admin",
        "Organization Owner",
        "Workspace Admin",
        "Reviewer",
        "Contributor",
        "Viewer",
    ]

    for role_name in ROLES_TO_SEED:
        query = select(Role).where(Role.name == role_name)
        result = await db.execute(query)
        existing_role = result.scalar_one_or_none()

        if not existing_role:
            new_role = Role(
                name=role_name,
                description=f"System generated default role for {role_name}",
            )

            db.add(new_role)

    await db.commit()


async def seed__rbac(db: AsyncSession) -> None:
    PERMISSIONS_TO_SEED = [
        {"name": "document:create", "description": "Can upload documents"},
        {"name": "document:read", "description": "Can view documents"},
        {"name": "document:update", "description": "Can edit documents"},
        {"name": "document:delete", "description": "Can delete documents"},
        # Folder Permissions
        {"name": "folder:create", "description": "Can create folders"},
        # Member Permissions
        {"name": "members:invite", "description": "Can invite members"},
        {"name": "members:manage_roles", "description": "Can assign or revoke roles"},
        {"name": "members:remove", "description": "Can remove members"},
        # Organization Permissions
        {"name": "organization:read", "description": "Can view organization details"},
        {
            "name": "organization:update",
            "description": "Can update organization & folders",
        },
        {"name": "organization:manage", "description": "Full organization management"},
    ]

    for permission_name in PERMISSIONS_TO_SEED:
        stmt = select(Permission).where(Permission.name == permission_name["name"])
        result = await db.execute(stmt)
        existing_permission = result.scalar_one_or_none()

        if not existing_permission:
            new_permission = Permission(
                name=permission_name["name"],
                description=permission_name["description"],
            )

            db.add(new_permission)

    await db.commit()


async def seed_role_permissions(db: AsyncSession) -> None:
    ROLE_PERMISSIONS_MAPPING = {
        # 1. Super Admin -> Full access to everything
        "Super Admin": [
            "document:create",
            "document:read",
            "document:update",
            "document:delete",
            "folder:create",
            "members:invite",
            "members:manage_roles",
            "members:remove",
            "organization:read",
            "organization:update",
            "organization:manage",
        ],
        # 2. Platform Admin -> Full access to everything
        "Platform Admin": [
            "document:create",
            "document:read",
            "document:update",
            "document:delete",
            "folder:create",
            "members:invite",
            "members:manage_roles",
            "members:remove",
            "organization:read",
            "organization:update",
            "organization:manage",
        ],
        # 3. Organization Owner -> Org manage + all document actions + member roles
        "Organization Owner": [
            "document:create",
            "document:read",
            "document:update",
            "document:delete",
            "folder:create",
            "members:invite",
            "members:manage_roles",
            "members:remove",
            "organization:read",
            "organization:update",
            "organization:manage",
        ],
        # 4. Workspace Admin -> Document CRUD + folder create + invite members
        "Workspace Admin": [
            "document:create",
            "document:read",
            "document:update",
            "document:delete",
            "folder:create",
            "members:invite",
            "organization:read",
            "organization:update",
        ],
        # 5. Reviewer -> Read documents + Update (comments/metadata/versions)
        "Reviewer": [
            "document:read",
            "document:update",
            "organization:read",
        ],
        # 6. Contributor -> Create, Read, Update documents
        "Contributor": [
            "document:create",
            "document:read",
            "document:update",
            "folder:create",
            "organization:read",
        ],
        # 7. Viewer -> Read-only access
        "Viewer": [
            "document:read",
            "organization:read",
        ],
    }
    repo = RBACRepository(db)
    missing: list[str] = []

    for role_name, perm_names in ROLE_PERMISSIONS_MAPPING.items():
        role = await repo.get_role_by_name(role_name)
        if not role:
            missing.append(f"role '{role_name}'")
            continue

        for perm_name in perm_names:
            perm = await repo.get_permission_by_name(perm_name)
            if perm is None:
                missing.append(f"permission '{perm_name}' (for role '{role_name}')")
                continue
            await repo.assign_permission_to_role(role, perm)

    await db.commit()

    if missing:
        print("⚠️  RBAC seeding finished with unresolved references:")
        for item in missing:
            print(f"   - {item}")
    else:
        print("✅ All roles and permissions resolved and assigned.")


# ---------------------------------------------------------
# MASTER RUNNER FUNCTION
# ---------------------------------------------------------
async def seed_all_rbac(db: AsyncSession) -> None:
    await seed__rbac(db)
    await seed_system_roles(db)
    await seed_role_permissions(db)
    print("✅ Full RBAC Seeding Completed Successfully!")
