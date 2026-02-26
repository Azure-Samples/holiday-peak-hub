import { redirect } from 'next/navigation';

/**
 * Password management is handled by Microsoft Entra ID.
 * Redirect users to the login page which triggers MSAL.
 */
export default function ForgotPasswordPage() {
  redirect('/auth/login');
}
