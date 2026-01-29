import Link from "next/link";
import CenteredForm from "layouts/centered-form";
import CreateAccount from "@/components/sample-forms/create-account";

const Index: React.FC = () => {
  return (
    <CenteredForm
      title="Create account"
      subtitle="Please enter your name, email address and password to create an account">
      <CreateAccount />

      <div className="flex flex-row w-full mt-4">
        <span className="mr-1">Already have an account?</span>
        <span>
          <Link href="/login" className="text-blue-500">
            Login here
          </Link>
        </span>
      </div>
      <div className="w-full">
        <span>
          <Link href="/forgot-password" className="text-blue-500">
            Forgot password?
          </Link>
        </span>
      </div>
    </CenteredForm>
  );
};

export default Index;
