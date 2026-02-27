import { redirect } from 'next/navigation';

/**
 * Signup page — registration is handled by Microsoft Entra ID.
 * Redirect users to the login page where they can sign in / sign up
 * with their Microsoft account.
 */
export default function SignupPage() {
  redirect('/auth/login');
}
