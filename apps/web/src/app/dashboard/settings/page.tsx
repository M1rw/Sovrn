import { Metadata } from 'next';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { SettingsForm } from './settings-form';

export const metadata: Metadata = {
  title: 'Settings',
};

export default async function SettingsPage() {
  const session = await getServerSession(authOptions);

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground">
          Manage your account and preferences
        </p>
      </div>

      <div className="space-y-6">
        {/* Profile Section */}
        <section className="rounded-xl border bg-card p-6">
          <h2 className="font-semibold text-lg mb-4">Profile</h2>
          <SettingsForm user={session!.user} />
        </section>

        {/* Preferences Section */}
        <section className="rounded-xl border bg-card p-6">
          <h2 className="font-semibold text-lg mb-4">Preferences</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Default Locale</p>
                <p className="text-sm text-muted-foreground">
                  Default region for new projects
                </p>
              </div>
              <select className="px-3 py-1.5 rounded-md border bg-background text-sm">
                <option value="en-US">🇺🇸 English (US)</option>
                <option value="en-GB">🇬🇧 English (UK)</option>
                <option value="de-DE">🇩🇪 German</option>
                <option value="fr-FR">🇫🇷 French</option>
                <option value="es-ES">🇪🇸 Spanish</option>
              </select>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Email Notifications</p>
                <p className="text-sm text-muted-foreground">
                  Receive emails about your projects
                </p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked="true"
                className="relative inline-flex h-6 w-11 items-center rounded-full bg-primary transition"
              >
                <span className="sr-only">Enable notifications</span>
                <span className="translate-x-6 inline-block h-4 w-4 transform rounded-full bg-white transition" />
              </button>
            </div>
          </div>
        </section>

        {/* Danger Zone */}
        <section className="rounded-xl border border-destructive/20 bg-destructive/5 p-6">
          <h2 className="font-semibold text-lg text-destructive mb-4">
            Danger Zone
          </h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Delete Account</p>
                <p className="text-sm text-muted-foreground">
                  Permanently delete your account and all data
                </p>
              </div>
              <button className="px-4 py-2 rounded-md border border-destructive text-destructive text-sm font-medium hover:bg-destructive hover:text-destructive-foreground transition">
                Delete Account
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
