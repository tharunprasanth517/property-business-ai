"""
Root URL configuration for Property Business AI.

Each installed app will register its own urls.py here as phases are
implemented. For now this file provides only the admin route and a
health-check placeholder.
"""

from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    # Django admin panel
    path("admin/", admin.site.urls),

    # ---------------------------------------------------------------------------
    # Application URL namespaces — uncommented as each phase is built
    # ---------------------------------------------------------------------------

    # Phase 1A — Authentication
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),

    # Phase 2 — Business multi-tenancy
    path("businesses/", include("apps.businesses.urls", namespace="businesses")),

    # Root redirect — send visitors to login; logged-in users handled by dashboard view
    path("", RedirectView.as_view(url="/accounts/login/", permanent=False)),

    # Phase 3 — Products & Inventory
    path("products/", include("apps.products.urls", namespace="products")),
    path("inventory/", include("apps.inventory.urls", namespace="inventory")),

    # Phase 4 — Transactions
    # path("transactions/", include("apps.transactions.urls", namespace="transactions")),

    # Phase 5 — Analytics & Dashboard
    # path("dashboard/", include("apps.analytics.urls", namespace="analytics")),

    # Phase 6 — AI Action Plan
    # path("ai/", include("apps.ai_engine.urls", namespace="ai_engine")),

    # Phase 7 — Data Importer
    # path("import/", include("apps.data_importer.urls", namespace="data_importer")),
]
