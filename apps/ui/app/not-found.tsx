'use client';

import Link from "next/link";
import Image from "next/image";

import Layout from "@/layouts/centered";


const NotFound = () => {
  return (
    <Layout>
      <div className="flex flex-col w-full max-w-xl text-center">
        <Image
          className="object-contain w-auto mb-8"
          height={64}
          width={64}
          src="/images/illustration.svg"
          alt="Not found illustration"
        />
        <h1 className="text-6xl text-blue-500 mb-4">404</h1>
        <h3 className="text-4xl text-blue-500 mb-4">Oops!</h3>

        <div className="mb-8 text-center text-gray-900 dark:text-white">
          The page you were looking for does not exist. Please check the URL and try again.
        </div>
        <div className="flex w-full">
          <Link href="/" className="w-full px-6 py-3 text-base font-bold text-white uppercase bg-blue-500 rounded-lg hover:bg-blue-600">
            Back Home
          </Link>
        </div>
      </div>
    </Layout>
  );
};

export default NotFound;
