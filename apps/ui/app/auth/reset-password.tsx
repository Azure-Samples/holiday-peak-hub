import { redirect } from 'next/navigation';

/**
 * Password resets are managed by Microsoft Entra ID.
 * Redirect users to the login page.
 */
export default function ResetPasswordPage() {
  redirect('/auth/login');
}
