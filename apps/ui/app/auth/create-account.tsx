import { redirect } from 'next/navigation';

/**
 * Account creation is managed by Microsoft Entra ID.
 * Redirect users to the login page which triggers MSAL signup.
 */
export default function CreateAccountPage() {
  redirect('/auth/login');
}


export default Index;
