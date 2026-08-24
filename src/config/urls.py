"""
Root URL configuration for Property Business AI.

Each installed app will register its own urls.py here as phases are
implemented. For now this file provides only the admin route and a
health-check placeholder.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Django admin panel
    path("admin/", admin.site.urls),

    # ---------------------------------------------------------------------------
    # Application URL namespaces — uncommented as each phase is built
    # ---------------------------------------------------------------------------

    # Phase 2 — Authentication & Business Setup
    # path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    # path("businesses/", include("apps.businesses.urls", namespace="businesses")),

    # Phase 3 — Products & Inventory
    # path("products/", include("apps.products.urls", namespace="products")),
    # path("inventory/", include("apps.inventory.urls", namespace="inventory")),

    # Phase 4 — Transactions
    # path("transactions/", include("apps.transactions.urls", namespace="transactions")),

    # Phase 5 — Analytics & Dashboard
    # path("dashboard/", include("apps.analytics.urls", namespace="analytics")),

    # Phase 6 — AI Action Plan
    # path("ai/", include("apps.ai_engine.urls", namespace="ai_engine")),

    # Phase 7 — Data Importer
    # path("import/", include("apps.data_importer.urls", namespace="data_importer")),
]
