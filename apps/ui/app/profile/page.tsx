'use client';

import React, { useState } from 'react';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Button } from '@/components/atoms/Button';
import { Input } from '@/components/atoms/Input';
import { Tabs } from '@/components/molecules/Tabs';
import { Badge } from '@/components/atoms/Badge';
import { 
  FiUser, FiMail, FiPhone, FiMapPin, FiCreditCard,
  FiLock, FiBell, FiShield, FiEdit2, FiTrash2, FiPlus
} from 'react-icons/fi';

export default function ProfilePage() {
  const [isEditing, setIsEditing] = useState(false);
  const [profileData, setProfileData] = useState({
    firstName: 'John',
    lastName: 'Doe',
    email: 'john.doe@example.com',
    phone: '+1 (555) 123-4567',
    dateOfBirth: '1990-01-15',
  });

  const savedAddresses = [
    {
      id: 1,
      type: 'Home',
      name: 'John Doe',
      address: '123 Main St',
      city: 'New York',
      state: 'NY',
      zipCode: '10001',
      isDefault: true,
    },
    {
      id: 2,
      type: 'Work',
      name: 'John Doe',
      address: '456 Office Plaza',
      city: 'New York',
      state: 'NY',
      zipCode: '10002',
      isDefault: false,
    },
  ];

  const paymentMethods = [
    {
      id: 1,
      type: 'Visa',
      last4: '4242',
      expiry: '12/25',
      isDefault: true,
    },
    {
      id: 2,
      type: 'Mastercard',
      last4: '8888',
      expiry: '08/26',
      isDefault: false,
    },
  ];

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault();
    setIsEditing(false);
    // Will be replaced with API call
    console.log('Profile saved:', profileData);
  };

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
                        {profileData.firstName.charAt(0)}{profileData.lastName.charAt(0)}
                      </div>
                      <div>
                        <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                          {profileData.firstName} {profileData.lastName}
                        </h2>
                        <p className="text-gray-600 dark:text-gray-400">
                          Member since Jan 2024
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
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">
                          First Name
                        </label>
                        <Input
                          type="text"
                          value={profileData.firstName}
                          onChange={(e) => setProfileData({...profileData, firstName: e.target.value})}
                          disabled={!isEditing}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">
                          Last Name
                        </label>
                        <Input
                          type="text"
                          value={profileData.lastName}
                          onChange={(e) => setProfileData({...profileData, lastName: e.target.value})}
                          disabled={!isEditing}
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">
                        Email Address
                      </label>
                      <Input
                        type="email"
                        value={profileData.email}
                        onChange={(e) => setProfileData({...profileData, email: e.target.value})}
                        disabled={!isEditing}
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

                    <div>
                      <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">
                        Date of Birth
                      </label>
                      <Input
                        type="date"
                        value={profileData.dateOfBirth}
                        onChange={(e) => setProfileData({...profileData, dateOfBirth: e.target.value})}
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
                        >
                          Save Changes
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
                <div className="space-y-4">
                  {savedAddresses.map((address) => (
                    <Card key={address.id} className="p-6">
                      <div className="flex items-start justify-between">
                        <div className="flex gap-4">
                          <div className="w-12 h-12 bg-cyan-100 dark:bg-cyan-900 rounded-lg flex items-center justify-center flex-shrink-0">
                            <FiMapPin className="w-6 h-6 text-cyan-500 dark:text-cyan-300" />
                          </div>
                          <div>
                            <div className="flex items-center gap-2 mb-2">
                              <h3 className="font-semibold text-gray-900 dark:text-white">
                                {address.type}
                              </h3>
                              {address.isDefault && (
                                <Badge className="bg-lime-100 text-lime-700 dark:bg-lime-900 dark:text-lime-300 text-xs">
                                  Default
                                </Badge>
                              )}
                            </div>
                            <p className="text-gray-600 dark:text-gray-400 text-sm">
                              {address.name}
                            </p>
                            <p className="text-gray-600 dark:text-gray-400 text-sm">
                              {address.address}
                            </p>
                            <p className="text-gray-600 dark:text-gray-400 text-sm">
                              {address.city}, {address.state} {address.zipCode}
                            </p>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button variant="outline" size="sm">
                            <FiEdit2 className="w-4 h-4" />
                          </Button>
                          <Button variant="outline" size="sm">
                            <FiTrash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </Card>
                  ))}
                  <Button className="w-full bg-ocean-500 hover:bg-ocean-600 dark:bg-ocean-300 dark:hover:bg-ocean-400 text-white dark:text-gray-900">
                    <FiPlus className="mr-2 w-4 h-4" />
                    Add New Address
                  </Button>
                </div>
              ),
            },
            {
              id: 'payment',
              label: 'Payment Methods',
              content: (
                <div className="space-y-4">
                  {paymentMethods.map((method) => (
                    <Card key={method.id} className="p-6">
                      <div className="flex items-center justify-between">
                        <div className="flex gap-4">
                          <div className="w-12 h-12 bg-ocean-100 dark:bg-ocean-900 rounded-lg flex items-center justify-center">
                            <FiCreditCard className="w-6 h-6 text-ocean-500 dark:text-ocean-300" />
                          </div>
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              <h3 className="font-semibold text-gray-900 dark:text-white">
                                {method.type} •••• {method.last4}
                              </h3>
                              {method.isDefault && (
                                <Badge className="bg-lime-100 text-lime-700 dark:bg-lime-900 dark:text-lime-300 text-xs">
                                  Default
                                </Badge>
                              )}
                            </div>
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                              Expires {method.expiry}
                            </p>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button variant="outline" size="sm">
                            <FiEdit2 className="w-4 h-4" />
                          </Button>
                          <Button variant="outline" size="sm">
                            <FiTrash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </Card>
                  ))}
                  <Button className="w-full bg-ocean-500 hover:bg-ocean-600 dark:bg-ocean-300 dark:hover:bg-ocean-400 text-white dark:text-gray-900">
                    <FiPlus className="mr-2 w-4 h-4" />
                    Add Payment Method
                  </Button>
                </div>
              ),
            },
            {
              id: 'security',
              label: 'Security',
              content: (
                <Card className="p-6 space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                      <FiLock className="mr-2 text-ocean-500 dark:text-ocean-300" />
                      Change Password
                    </h3>
                    <form className="space-y-4">
                      <div>
                        <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">
                          Current Password
                        </label>
                        <Input type="password" />
                      </div>
                      <div>
                        <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">
                          New Password
                        </label>
                        <Input type="password" />
                      </div>
                      <div>
                        <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">
                          Confirm New Password
                        </label>
                        <Input type="password" />
                      </div>
                      <Button className="bg-ocean-500 hover:bg-ocean-600 dark:bg-ocean-300 dark:hover:bg-ocean-400 text-white dark:text-gray-900">
                        Update Password
                      </Button>
                    </form>
                  </div>

                  <div className="pt-6 border-t border-gray-200 dark:border-gray-700">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                      <FiShield className="mr-2 text-lime-500 dark:text-lime-300" />
                      Two-Factor Authentication
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                      Add an extra layer of security to your account
                    </p>
                    <Button className="bg-lime-500 hover:bg-lime-600 dark:bg-lime-400 dark:hover:bg-lime-500 text-white dark:text-gray-900">
                      Enable 2FA
                    </Button>
                  </div>
                </Card>
              ),
            },
            {
              id: 'preferences',
              label: 'Preferences',
              content: (
                <Card className="p-6 space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                      <FiBell className="mr-2 text-cyan-500 dark:text-cyan-300" />
                      Notifications
                    </h3>
                    <div className="space-y-4">
                      <NotificationToggle
                        label="Order Updates"
                        description="Get notified about your order status"
                        defaultChecked={true}
                      />
                      <NotificationToggle
                        label="Promotional Emails"
                        description="Receive exclusive deals and offers"
                        defaultChecked={true}
                      />
                      <NotificationToggle
                        label="Product Recommendations"
                        description="Personalized product suggestions"
                        defaultChecked={false}
                      />
                      <NotificationToggle
                        label="Newsletter"
                        description="Weekly newsletter with updates"
                        defaultChecked={true}
                      />
                    </div>
                  </div>
                </Card>
              ),
            },
          ]}
        />
      </div>
    </MainLayout>
  );
}

function NotificationToggle({ label, description, defaultChecked }: {
  label: string;
  description: string;
  defaultChecked: boolean;
}) {
  const [checked, setChecked] = React.useState(defaultChecked);

  return (
    <div className="flex items-center justify-between py-3">
      <div>
        <h4 className="font-medium text-gray-900 dark:text-white">{label}</h4>
        <p className="text-sm text-gray-600 dark:text-gray-400">{description}</p>
      </div>
      <button
        onClick={() => setChecked(!checked)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
          checked ? 'bg-ocean-500 dark:bg-ocean-300' : 'bg-gray-300 dark:bg-gray-600'
        }`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            checked ? 'translate-x-6' : 'translate-x-1'
          }`}
        />
      </button>
    </div>
  );
}
