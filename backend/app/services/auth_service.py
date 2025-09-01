"""
Authentication service - Service Account Mode
No individual user authentication required
"""

from ..services.spotify_service import spotify_service


async def get_service_account_info():
    """Get service account information"""
    service_validation = await spotify_service.validate_service_account()
    return service_validation
