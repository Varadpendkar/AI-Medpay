// auth_google.js - small helper to open Google OAuth (we trigger server flow)
document.addEventListener('DOMContentLoaded', function () {
  const gSignIn = document.getElementById('google-signin');
  const gSignUp = document.getElementById('google-signup');

  if (gSignIn) {
    gSignIn.addEventListener('click', () => {
      // redirect to server-side Google OAuth start
      window.location.href = '/auth/google';
    });
  }
  if (gSignUp) {
    gSignUp.addEventListener('click', () => {
      window.location.href = '/auth/google?next=/register';
    });
  }
});