from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class ForcePasswordResetMiddleware:
    """
    If a logged-in user still has must_reset_password=True — a newly
    created account, or an account whose password an administrator just
    reset — every request is redirected to the mandatory password-reset
    screen until they set their own password. This runs after Django's
    AuthenticationMiddleware, so request.user is already resolved.
    """

    # URL names a flagged user is still allowed to reach.
    EXEMPT_URL_NAMES = ('force_password_reset', 'logout')

    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_paths = {reverse(name) for name in self.EXEMPT_URL_NAMES}

    def __call__(self, request):
        user = getattr(request, 'user', None)

        if (
            user is not None
            and user.is_authenticated
            and getattr(user, 'must_reset_password', False)
            and request.path not in self.exempt_paths
            and not request.path.startswith(settings.STATIC_URL)
            and not request.path.startswith('/admin/')
        ):
            return redirect('force_password_reset')

        return self.get_response(request)