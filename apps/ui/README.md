###D-board

D-board is an advanced, responsive admin template built with Typescript, React, Redux Toolkit, Next.js and Tailwind CSS.

It includes 2 different layouts, 2 background color styles, 100+ components in every layout and lots of widgets and custom made reusable components to help you kickstart your next React project or application.

To install, first make sure the correct `node` and `npm` are installed in your system.

To check if they are installed correctly, run the following commands, which should print at least the following versions.

`node -v` -> v16.13.0 LTS
`npm -v` -> 8.1.0

D-board is 100% ready to use. Just unzip the included files and run the following commands:

`npm install` to install all the required dependencies
`npm run dev` to run the development server
Open http://localhost:3000

To build and run a production ready bundle, run the following commands:

`npm run build`
`npm run start` to preview the generated files

The template includes the following structural elements:

- Navbar
- Left sidebar
- Right sidebar
- Main content section
- Centered layouts for forms

D-board uses the default Next.js file and folder code structure. For more information on the project and to familiarize yourself with the file and folder structure used in a Next.js application, please go to the Next.js website.

All pages are located in the `src/pages` folder.

All components and widgets are located in the `src/components` folder.

All layouts and structural views are located in the `src/layouts` folder.

CSS files are located in the `src/css` folder.

####Important folders in the template

`src/components`
Includes all the components ands widgets included in the template

`src/css`
Includes CSS files

`src/layouts`
Includes all layouts and structural views

`src/css/layouts`
Includes CSS for all the included layouts

`src/css/components`
Includes CSS for some of the included components, although most components use tailwind classes

`functions`
Includes helpers and functions used in the template

`json`
Includes sample json files with data used in some views and components

`src/slices`
Includes Redux Toolkit slices used in the app

`src/slices/navigation`
Includes menus and navigation files that are used in the left sidebar and top navigation components

`src/pages`
Includes all pages and sample views

`public`
Includes all the static assets and content used in the template

####Important files in the template

`src/store.tsx`
Redux Toolkit config and global store

`tailwind.config.js`
Tailwind CSS default configuration

`src/pages/index.tsx`
Template index file

`src/pages/_app.tsx`
Next.js custom App file. All CSS files are imported here

`src/pages/_document.tsx`
Next.js custom Document file. Custom HTML meta tags are defined here

`postcss.config.js`
PostCSS configuration for plugins used in the template
