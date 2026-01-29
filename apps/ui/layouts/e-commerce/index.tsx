import clsx from "clsx";
import Head from "next/head";
import {useAppSelector} from "@/store";
import Navbar1 from "@/components/navbar-1";
import LeftSidebar2 from "@/components/left-sidebar-2";
import RightSidebar1 from "@/components/right-sidebar-1";
import NProgressHandler from '@/components/NprogressHandler';

export type ECommerceProps = {
  children: React.ReactNode;
};

const Ecommerce: React.FC<ECommerceProps> = ({children}) => {
  const config = useAppSelector((state) => state.config);
  const {background, collapsed} = config;

  return (
    <>
      <NProgressHandler />
      <Head>
        <title>D-board</title>
      </Head>
      <div
        data-layout="e-commerce"
        data-collapsed={collapsed}
        className={clsx(
          "font-sans antialiased text-sm disable-scrollbars",
          background === "dark" ? "dark" : "light",
          collapsed ? "collapsed" : ""
        )}>
        <RightSidebar1 />
        <div className="flex flex-row items-stretch w-full min-w-full">
          <LeftSidebar2 />
          <div className="z-0 w-full bg-gray-50 text-gray-900 dark:bg-gray-900 dark:text-white">
            <Navbar1 />
            <div className="w-full min-h-screen p-4">{children}</div>
          </div>
        </div>
      </div>
    </>
  );
};
export default Ecommerce;
