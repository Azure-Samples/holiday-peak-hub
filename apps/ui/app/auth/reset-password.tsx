import Link from "next/link";
import CenteredForm from "layouts/centered-form";
import ResetPassword from "@/components/sample-forms/reset-password";

const Index: React.FC = () => {
  return (
    <CenteredForm
      title="Reset password"
      subtitle="Please enter your new password to reset your account">
      <ResetPassword />

      <div className="flex flex-row w-full mt-3">
        <span className="mr-1">New user?</span>
        <span>
          <Link href="/create-account" className="text-blue-500">
            Sign up here
          </Link>
        </span>
      </div>
      <div className="flex flex-row w-full">
        <span className="mr-1">Already have an account?</span>
        <span>
          <Link href="/login" className="text-blue-500">
            Login here
          </Link>
        </span>
      </div>
    </CenteredForm>
  );
};

export default Index;
