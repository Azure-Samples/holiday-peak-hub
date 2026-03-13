'use client';

import React, { useEffect, useState } from 'react';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Button } from '@/components/atoms/Button';
import { Input } from '@/components/atoms/Input';
import { Tabs } from '@/components/molecules/Tabs';
import { useUserProfile, useUpdateProfile } from '@/lib/hooks/useUser';
import { 
  FiEdit2
} from 'react-icons/fi';

export default function ProfilePage() {
  const [isEditing, setIsEditing] = useState(false);
  const { data: userProfile, isLoading: profileLoading } = useUserProfile();
  const updateProfile = useUpdateProfile();

  const [profileData, setProfileData] = useState({
    name: '',
    phone: '',
  });

  const hasInitialized = React.useRef(false);
  useEffect(() => {
    if (userProfile && !hasInitialized.current) {
      hasInitialized.current = true;
      setProfileData({
        name: userProfile.name ?? '',
        phone: userProfile.phone ?? '',
      });
    }
  }, [userProfile]);

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault();
    updateProfile.mutate(
      { name: profileData.name, phone: profileData.phone || undefined },
      { onSuccess: () => setIsEditing(false) }
    );
  };

  const displayName = userProfile?.name ?? profileData.name;
  const initials = displayName
    ? displayName.split(' ').map((n) => n.charAt(0)).slice(0, 2).join('')
    : '?';

  return (
    <MainLayout>
      <div className="max-w-6xl mx-auto py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            My Profile
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Manage your account settings and preferences
          </p>
        </div>

        <Tabs
          tabs={[
            {
              id: 'personal',
              label: 'Personal Information',
              content: (
                <Card className="p-6">
                  <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-4">
                      <div className="w-20 h-20 bg-ocean-500 dark:bg-ocean-300 rounded-full flex items-center justify-center text-white dark:text-gray-900 text-2xl font-bold">
                        {initials}
                      </div>
                      <div>
                        <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                          {profileLoading ? '…' : displayName}
                        </h2>
                        <p className="text-gray-600 dark:text-gray-400">
                          {userProfile?.email ?? ''}
                        </p>
                        <p className="text-gray-500 dark:text-gray-500 text-sm">
                          Member since {userProfile ? new Date(userProfile.created_at).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }) : '…'}
                        </p>
                      </div>
                    </div>
                    {!isEditing && (
                      <Button
                        variant="outline"
                        onClick={() => setIsEditing(true)}
                        className="border-ocean-500 text-ocean-500 dark:border-ocean-300 dark:text-ocean-300"
                      >
                        <FiEdit2 className="mr-2 w-4 h-4" />
                        Edit Profile
                      </Button>
                    )}
                  </div>

                  <form onSubmit={handleSaveProfile} className="space-y-6">
                    <div>
                      <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">
                        Full Name
                      </label>
                      <Input
                        type="text"
                        value={profileData.name}
                        onChange={(e) => setProfileData({...profileData, name: e.target.value})}
                        disabled={!isEditing}
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">
                        Email Address
                      </label>
                      <Input
                        type="email"
                        value={userProfile?.email ?? ''}
                        disabled
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">
                        Phone Number
                      </label>
                      <Input
                        type="tel"
                        value={profileData.phone}
                        onChange={(e) => setProfileData({...profileData, phone: e.target.value})}
                        disabled={!isEditing}
                      />
                    </div>

                    {isEditing && (
                      <div className="flex gap-4">
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => setIsEditing(false)}
                          className="flex-1"
                        >
                          Cancel
                        </Button>
                        <Button
                          type="submit"
                          className="flex-1 bg-ocean-500 hover:bg-ocean-600 dark:bg-ocean-300 dark:hover:bg-ocean-400 text-white dark:text-gray-900"
                          disabled={updateProfile.isPending}
                        >
                          {updateProfile.isPending ? 'Saving…' : 'Save Changes'}
                        </Button>
                      </div>
                    )}
                  </form>
                </Card>
              ),
            },
            {
              id: 'addresses',
              label: 'Addresses',
              content: (
                <UnsupportedTabState message="Addresses are not available in the current API contract." />
              ),
            },
            {
              id: 'payment',
              label: 'Payment Methods',
              content: (
                <UnsupportedTabState message="Payment methods are not available in the current API contract." />
              ),
            },
            {
              id: 'security',
              label: 'Security',
              content: (
                <UnsupportedTabState message="Security settings are not available in the current API contract." />
              ),
            },
            {
              id: 'preferences',
              label: 'Preferences',
              content: (
                <UnsupportedTabState message="Preferences are not available in the current API contract." />
              ),
            },
          ]}
        />
      </div>
    </MainLayout>
  );
}

function UnsupportedTabState({ message }: { message: string }) {
  const headingId = React.useId();

  return (
    <Card className="p-6" role="note" aria-labelledby={headingId}>
      <h3 id={headingId} className="text-base font-semibold text-gray-900 dark:text-white mb-2">
        Feature unavailable
      </h3>
      <p className="text-sm text-gray-600 dark:text-gray-400">{message}</p>
    </Card>
  );
}
