import {createSlice, PayloadAction} from "@reduxjs/toolkit";

// Define a type for the slice state
interface LeftSidebarState {
  showButtonText: boolean;
  showSectionTitle: boolean;
  showLogo: boolean;
  showCard: boolean;
  showAccountLinks: boolean;
  showProjects: boolean;
  showTags: boolean;
  card: number;
}

// Define the initial state using that type
const initialState: LeftSidebarState = {
  showButtonText: true,
  showSectionTitle: true,
  showLogo: true,
  showCard: true,
  showAccountLinks: false,
  showProjects: true,
  showTags: true,
  card: 1,
};

export const leftSidebarSlice = createSlice({
  name: "leftSidebar",
  // `createSlice` will infer the state type from the `initialState` argument
  initialState,
  reducers: {
    setLeftSidebar: (
      state,
      action: PayloadAction<Partial<LeftSidebarState>>
    ) => {
      return {
        ...state,
        ...action.payload,
      };
    },
  },
});

export const {setLeftSidebar} = leftSidebarSlice.actions;

export default leftSidebarSlice.reducer;
