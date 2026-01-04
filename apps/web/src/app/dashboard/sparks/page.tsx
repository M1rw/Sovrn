import { Metadata } from 'next';
import { getServerSession } from 'next-auth';
import Link from 'next/link';
import { authOptions } from '@/lib/auth';
import { sparksApi } from '@/lib/api';
import { Sparkles, Plus, History, CreditCard, CheckCircle2 } from 'lucide-react';
import { formatCurrency, formatRelativeTime } from '@/lib/utils';

export const metadata: Metadata = {
  title: 'Sparks',
};

export default async function SparksPage() {
  const session = await getServerSession(authOptions);

  let balance: { sparks_balance: number; sparks_used_total: number };
  let history: { items: any[]; total: number; page: number; page_size: number; pages: number };
  let plans: any[];

  try {
    [balance, history, plans] = await Promise.all([
      sparksApi.getBalance(session!.accessToken),
      sparksApi.getHistory(session!.accessToken),
      sparksApi.getPlans(),
    ]);
  } catch {
    balance = { sparks_balance: 0, sparks_used_total: 0 };
    history = { items: [], total: 0, page: 1, page_size: 10, pages: 0 };
    plans = [];
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Sparks</h1>
        <p className="text-muted-foreground">
          Manage your Spark balance and purchase more to generate websites
        </p>
      </div>

      {/* Balance Card */}
      <div className="rounded-xl bg-gradient-to-br from-primary/20 via-primary/10 to-transparent border p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">Current Balance</p>
            <p className="text-4xl font-bold mt-1 flex items-center gap-2">
              <Sparkles className="h-8 w-8 text-primary" />
              {balance.sparks_balance}
              <span className="text-lg font-normal text-muted-foreground">Sparks</span>
            </p>
            <p className="text-sm text-muted-foreground mt-2">
              {balance.sparks_used_total} Sparks used total
            </p>
          </div>
          <Link
            href="#plans"
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition"
          >
            <Plus className="h-4 w-4" />
            Buy Sparks
          </Link>
        </div>
      </div>

      {/* Spark Plans */}
      <section id="plans">
        <h2 className="text-lg font-semibold mb-4">Spark Packs</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {plans.length > 0 ? (
            plans.map((plan) => (
              <SparkPlanCard key={plan.id} plan={plan} />
            ))
          ) : (
            <>
              <SparkPlanCard
                plan={{
                  id: 'starter',
                  name: 'Starter',
                  type: 'starter',
                  sparks_included: 10,
                  price_cents: 1000,
                  features: {},
                }}
              />
              <SparkPlanCard
                plan={{
                  id: 'growth',
                  name: 'Growth',
                  type: 'growth',
                  sparks_included: 50,
                  price_cents: 4000,
                  features: { popular: true },
                }}
                isPopular
              />
              <SparkPlanCard
                plan={{
                  id: 'pro',
                  name: 'Pro',
                  type: 'pro',
                  sparks_included: 150,
                  price_cents: 10000,
                  features: {},
                }}
              />
              <SparkPlanCard
                plan={{
                  id: 'enterprise',
                  name: 'Enterprise',
                  type: 'enterprise',
                  sparks_included: 500,
                  price_cents: 25000,
                  features: {},
                }}
              />
            </>
          )}
        </div>
        <p className="text-sm text-muted-foreground mt-4">
          💳 We accept manual payments via bank transfer, PayPal, and crypto.
          Contact us for payment instructions.
        </p>
      </section>

      {/* Transaction History */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <History className="h-5 w-5" />
          <h2 className="text-lg font-semibold">Transaction History</h2>
        </div>

        {history.items.length > 0 ? (
          <div className="rounded-xl border bg-card overflow-hidden">
            <table className="w-full">
              <thead className="border-b bg-muted/50">
                <tr>
                  <th className="text-left text-sm font-medium text-muted-foreground px-4 py-3">
                    Type
                  </th>
                  <th className="text-left text-sm font-medium text-muted-foreground px-4 py-3">
                    Description
                  </th>
                  <th className="text-right text-sm font-medium text-muted-foreground px-4 py-3">
                    Amount
                  </th>
                  <th className="text-right text-sm font-medium text-muted-foreground px-4 py-3">
                    Balance
                  </th>
                  <th className="text-right text-sm font-medium text-muted-foreground px-4 py-3">
                    Date
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {history.items.map((entry) => (
                  <tr key={entry.id} className="hover:bg-muted/30 transition">
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                          entry.type === 'credit'
                            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                            : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
                        }`}
                      >
                        {entry.type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {entry.description || '-'}
                    </td>
                    <td
                      className={`px-4 py-3 text-sm text-right font-medium ${
                        entry.amount > 0 ? 'text-green-600' : 'text-muted-foreground'
                      }`}
                    >
                      {entry.amount > 0 ? '+' : ''}
                      {entry.amount}
                    </td>
                    <td className="px-4 py-3 text-sm text-right text-muted-foreground">
                      {entry.balance_after}
                    </td>
                    <td className="px-4 py-3 text-sm text-right text-muted-foreground">
                      {formatRelativeTime(entry.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="rounded-xl border border-dashed p-8 text-center">
            <History className="h-12 w-12 mx-auto text-muted-foreground/50" />
            <p className="mt-2 font-medium">No transactions yet</p>
            <p className="text-sm text-muted-foreground">
              Your Spark transactions will appear here
            </p>
          </div>
        )}
      </section>
    </div>
  );
}

interface SparkPlanCardProps {
  plan: {
    id: string;
    name: string;
    type: string;
    sparks_included: number;
    price_cents: number;
    features: Record<string, unknown>;
  };
  isPopular?: boolean;
}

function SparkPlanCard({ plan, isPopular }: SparkPlanCardProps) {
  const pricePerSpark = (plan.price_cents / plan.sparks_included / 100).toFixed(2);

  return (
    <div
      className={`rounded-xl border p-6 relative ${
        isPopular ? 'border-primary ring-1 ring-primary' : ''
      }`}
    >
      {isPopular && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary text-primary-foreground px-3 py-0.5 rounded-full text-xs font-medium">
          Most Popular
        </span>
      )}
      <h3 className="font-semibold text-lg">{plan.name}</h3>
      <div className="mt-2">
        <span className="text-3xl font-bold">
          {formatCurrency(plan.price_cents)}
        </span>
      </div>
      <div className="flex items-center gap-2 mt-3 text-primary">
        <Sparkles className="h-5 w-5" />
        <span className="font-semibold">{plan.sparks_included} Sparks</span>
      </div>
      <p className="text-sm text-muted-foreground mt-1">
        ${pricePerSpark} per Spark
      </p>
      <ul className="mt-4 space-y-2 text-sm">
        <li className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-primary" />
          {plan.sparks_included} website generations
        </li>
        <li className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-primary" />
          Never expires
        </li>
        <li className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-primary" />
          Full code export
        </li>
      </ul>
      <button className="w-full mt-6 inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition">
        <CreditCard className="h-4 w-4" />
        Purchase
      </button>
    </div>
  );
}
