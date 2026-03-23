import React from 'react';
import { render, waitFor } from '@testing-library/react';

import LogoutPage from '../../app/logout/page';

const replaceMock = jest.fn();
const refreshMock = jest.fn();
const logoutMock = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    replace: replaceMock,
    refresh: refreshMock,
  }),
}));

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    logout: logoutMock,
  }),
}));

describe('/logout page', () => {
  beforeEach(() => {
    replaceMock.mockClear();
    refreshMock.mockClear();
    logoutMock.mockReset();
  });

  it('executes logout and redirects to login', async () => {
    logoutMock.mockResolvedValue(undefined);

    render(<LogoutPage />);

    await waitFor(() => {
      expect(logoutMock).toHaveBeenCalledTimes(1);
      expect(replaceMock).toHaveBeenCalledWith('/auth/login');
      expect(refreshMock).toHaveBeenCalledTimes(1);
    });
  });

  it('still redirects to login when logout rejects', async () => {
    logoutMock.mockRejectedValue(new Error('logout failed'));

    render(<LogoutPage />);

    await waitFor(() => {
      expect(logoutMock).toHaveBeenCalledTimes(1);
      expect(replaceMock).toHaveBeenCalledWith('/auth/login');
      expect(refreshMock).toHaveBeenCalledTimes(1);
    });
  });
});