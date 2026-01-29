import Link from "next/link";

const EmailConfirmation: React.FC = () => {
  return (
    <div className="flex flex-col w-full max-w-xl text-center">
      <img
        className="object-contain w-auto h-64 mb-8"
        src="/images/illustration.svg"
        alt="svg"
      />
      <div className="mb-8 text-center">You have succesfully signed out.</div>
      <div className="flex w-full">
        <Link
          href="/"
          className="font-bold uppercase text-base px-6 py-3 rounded-lg w-full bg-blue-500 hover:bg-blue-600 text-white"
        >
          Go back
        </Link>
      </div>
    </div>
  );
};

export default EmailConfirmation;
