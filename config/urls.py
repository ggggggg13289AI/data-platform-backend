"""
URL configuration for Django Ninja API.
All endpoints under /api/v1/ prefix.
"""

from ninja import NinjaAPI
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static
from studies.api import router as studies_router
from studies.report_api import report_router
from studies.project_api import router as project_router
from studies.auth_api import auth_router

# Create Ninja API
api = NinjaAPI(
    title='医疗影像管理系统 API',  # Medical Imaging Management System API
    version='1.1.0',
    description='REST API for medical imaging examination and report management',
)

# Include routers with prefixes
api.add_router('/studies', studies_router, tags=['studies'])
api.add_router('/reports', report_router, tags=['reports'])
api.add_router('/auth', auth_router, tags=['authentication'])
api.add_router('', project_router)

# Health check endpoint
@api.get('/health')
def health_check(request):
    """Health check endpoint"""
    return {'status': 'ok', 'version': '1.0.0'}

# URL patterns
urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/v1/', api.urls),
    
    # Root endpoint with API info
    path('', lambda request: JsonResponse({
        'app': '医疗影像管理系统',
        'version': '1.0.0',
        'docs': '/api/v1/docs',
    })),
]

# Serve static files in development AND testing
# Always serve static files to support admin interface
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
