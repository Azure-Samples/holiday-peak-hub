export type CenteredProps = {
  children: React.ReactNode;
};

const Centered: React.FC<CenteredProps> = ({children}) => (
  <>
    <div
      data-layout="centered"
      className="w-full h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white">
      <div className="p-4 lg:p-0">{children}</div>
    </div>
  </>
);

export default Centered;
