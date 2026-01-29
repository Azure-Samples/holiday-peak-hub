import Link from "next/link";
import CenteredForm from "@/layouts/centered-form";
import ForgotPassword from "@/components/sample-forms/forgot-password";

const Index: React.FC = () => {
  return (
    <CenteredForm
      title="Forgot password"
      subtitle="Please enter your email address to recover your password">
      <ForgotPassword />
      <div className="w-full mt-2">
        <span>
          <Link href="/login" className="text-blue-500">
            Go back to login
          </Link>
        </span>
      </div>
    </CenteredForm>
  );
};

export default Index;
