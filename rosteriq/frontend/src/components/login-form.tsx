"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, CheckCircle2, LayoutGrid, LoaderCircle, ShieldCheck } from "lucide-react";
import { useAuth } from "@/components/auth-provider";

type FormMode = "welcome" | "login" | "register";
type SupabaseClient = NonNullable<ReturnType<typeof useAuth>["client"]>;

async function createManagerProfile(
  client: SupabaseClient,
  userId: string,
  fullName: string,
  email: string,
  employeeId: string,
) {
  const result = await client
    .from("manager_profiles")
    .insert({
      id: userId,
      full_name: fullName,
      work_email: email,
      employee_id: employeeId,
    })
    .select("id, full_name, work_email, employee_id, created_at")
    .single();

  if (!result.error || result.error.code !== "23505") {
    return result;
  }

  const { data, error } = await client
    .from("manager_profiles")
    .select("id, full_name, work_email, employee_id, created_at")
    .eq("id", userId)
    .maybeSingle();
  if (error || data) {
    return { data, error };
  }

  return result;
}

function getProfileErrorMessage(error: { code?: string; message: string }) {
  return error.code === "23505"
    ? "This employee ID is already associated with another manager profile."
    : error.message;
}

export default function LoginForm() {
  const router = useRouter();
  const { client, isLoading, refreshProfile, user } = useAuth();
  const [mode, setMode] = useState<FormMode>("welcome");
  const [pending, setPending] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [noticeMessage, setNoticeMessage] = useState("");

  useEffect(() => {
    if (!isLoading && user && !pending) {
      router.replace("/");
    }
  }, [isLoading, pending, router, user]);

  function changeMode(nextMode: FormMode) {
    setErrorMessage("");
    setNoticeMessage("");
    setMode(nextMode);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage("");
    setNoticeMessage("");

    if (!client) {
      setErrorMessage("Add your Supabase URL and public anon key to frontend/.env.local.");
      return;
    }

    const formData = new FormData(event.currentTarget);
    const email = String(formData.get("email") ?? "").trim().toLowerCase();
    const password = String(formData.get("password") ?? "");

    if (!email || !password) {
      setErrorMessage("Enter your email and password.");
      return;
    }

    const fullName = String(formData.get("fullName") ?? "").trim();
    const confirmPassword = String(formData.get("confirmPassword") ?? "");
    if (mode === "register") {
      if (!fullName || !confirmPassword) {
        setErrorMessage("Complete all required fields.");
        return;
      }
      if (password.length < 8) {
        setErrorMessage("Your password must be at least 8 characters.");
        return;
      }
      if (password !== confirmPassword) {
        setErrorMessage("The passwords do not match.");
        return;
      }
    }

    setPending(true);

    try {
      if (mode === "register") {
        const employeeId = `manager-${crypto.randomUUID()}`;
        const { data, error } = await client.auth.signUp({
          email,
          password,
          options: {
            data: {
              full_name: fullName,
              employee_id: employeeId,
            },
          },
        });
        if (error) {
          setErrorMessage(error.message);
          return;
        }
        if (!data.user) {
          setErrorMessage("Supabase created no user for this registration.");
          return;
        }

        if (!data.session) {
          setNoticeMessage(
            "Your account was created. Confirm your email, then log in to finish setting up your manager profile.",
          );
          return;
        }

        const { data: profile, error: profileError } = await createManagerProfile(
          client,
          data.user.id,
          fullName,
          email,
          employeeId,
        );
        if (profileError || !profile) {
          const { error: signOutError } = await client.auth.signOut();
          const message = profileError
            ? getProfileErrorMessage(profileError)
            : "Supabase returned no manager profile.";
          setErrorMessage(
            signOutError
              ? `Your account was created, but its manager profile could not be saved: ${message} Sign-out also failed: ${signOutError.message}`
              : `Your account was created, but its manager profile could not be saved: ${message}`,
          );
          return;
        }

        await refreshProfile(data.user.id);
      } else {
        const { data, error } = await client.auth.signInWithPassword({ email, password });
        if (error) {
          setErrorMessage(error.message);
          return;
        }

        const { data: profile, error: profileError } = await client
          .from("manager_profiles")
          .select("id")
          .eq("id", data.user.id)
          .maybeSingle();
        if (profileError) {
          const { error: signOutError } = await client.auth.signOut();
          setErrorMessage(
            signOutError
              ? `${profileError.message} Sign-out also failed: ${signOutError.message}`
              : profileError.message,
          );
          return;
        }

        if (!profile) {
          const metadataName = data.user.user_metadata.full_name;
          const metadataEmployeeId = data.user.user_metadata.employee_id;
          if (
            typeof metadataName !== "string" ||
            !metadataName.trim() ||
            typeof metadataEmployeeId !== "string" ||
            !metadataEmployeeId.trim()
          ) {
            const { error: signOutError } = await client.auth.signOut();
            const message = "This account is not configured as the Operations Manager.";
            setErrorMessage(
              signOutError ? `${message} Sign-out also failed: ${signOutError.message}` : message,
            );
            return;
          }

          const { error: saveError } = await createManagerProfile(
            client,
            data.user.id,
            metadataName.trim(),
            email,
            metadataEmployeeId.trim(),
          );
          if (saveError) {
            const { error: signOutError } = await client.auth.signOut();
            const message = getProfileErrorMessage(saveError);
            setErrorMessage(
              signOutError
                ? `Your login succeeded, but your manager profile could not be saved: ${message} Sign-out also failed: ${signOutError.message}`
                : `Your login succeeded, but your manager profile could not be saved: ${message}`,
            );
            return;
          }
        }

        await refreshProfile(data.user.id);
      }

      router.replace("/");
    } catch (error: unknown) {
      setErrorMessage(
        error instanceof Error ? error.message : "Authentication could not be completed.",
      );
    } finally {
      setPending(false);
    }
  }

  const isRegistration = mode === "register";

  return (
    <main className="min-h-screen bg-[#f7f8ff] px-4 py-8 sm:px-8 lg:px-12">
      <div className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl items-center gap-10 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16">
        <section className="mx-auto w-full max-w-xl">
          <Link href="/" className="mb-12 inline-flex items-center gap-3" aria-label="RosterIQ home">
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#4f46e5] text-white shadow-lg shadow-indigo-200">
              <LayoutGrid aria-hidden="true" className="h-6 w-6" />
            </span>
            <span>
              <span className="block font-display text-xl font-bold tracking-tight text-[#131b2e]">RosterIQ</span>
              <span className="block text-xs font-medium text-[#777587]">Workforce Intelligence</span>
            </span>
          </Link>
          <p className="mb-4 text-xs font-bold uppercase tracking-[0.18em] text-[#4f46e5]">
            Operations, in sync
          </p>
          <h1 className="font-display text-4xl font-bold leading-tight tracking-tight text-[#131b2e] sm:text-5xl">
            Your workforce.
            <br />
            In better balance.
          </h1>
          <p className="mt-5 max-w-lg text-base leading-7 text-[#5b5a6c]">
            A clearer view of coverage, capacity, and the people who keep every shift moving.
          </p>
          <div className="mt-9 grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-[#e4e6f4] bg-white p-4">
              <CheckCircle2 aria-hidden="true" className="mb-3 h-5 w-5 text-[#087e8b]" />
              <p className="text-sm font-semibold text-[#131b2e]">One operational view</p>
              <p className="mt-1 text-xs leading-5 text-[#777587]">Bring workforce health and shift coverage together.</p>
            </div>
            <div className="rounded-2xl border border-[#e4e6f4] bg-white p-4">
              <ShieldCheck aria-hidden="true" className="mb-3 h-5 w-5 text-[#4f46e5]" />
              <p className="text-sm font-semibold text-[#131b2e]">Built for managers</p>
              <p className="mt-1 text-xs leading-5 text-[#777587]">A focused roster view for Operations Managers.</p>
            </div>
          </div>
        </section>

        <section className="mx-auto w-full max-w-md rounded-3xl border border-[#e5e7f2] bg-white p-6 shadow-[0_24px_70px_rgba(27,35,72,0.10)] sm:p-9">
          {mode === "welcome" ? (
            <>
              <p className="text-sm font-semibold text-[#4f46e5]">Welcome to RosterIQ</p>
              <h2 className="mt-2 font-display text-2xl font-bold tracking-tight text-[#131b2e]">
                Your operations overview starts here.
              </h2>
              <p className="mt-3 text-sm leading-6 text-[#777587]">
                Sign in to continue to your workforce dashboard.
              </p>
              <button
                type="button"
                onClick={() => changeMode("login")}
                disabled={!client || isLoading}
                className="mt-8 flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-[#4f46e5] px-4 text-sm font-semibold text-white transition-colors hover:bg-[#3525cd] disabled:cursor-not-allowed disabled:opacity-60"
              >
                Log in as Operations Manager
                <ArrowRight aria-hidden="true" className="h-4 w-4" />
              </button>
              <p className="mt-5 text-center text-sm text-[#777587]">
                New to RosterIQ?{" "}
                <button
                  type="button"
                  onClick={() => changeMode("register")}
                  disabled={!client || isLoading}
                  className="font-semibold text-[#4f46e5] hover:text-[#3525cd] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Create Account
                </button>
              </p>
            </>
          ) : (
            <>
              <button
                type="button"
                onClick={() => changeMode("welcome")}
                className="mb-6 text-sm font-semibold text-[#4f46e5] hover:text-[#3525cd]"
              >
                &larr; Back
              </button>
              <p className="text-sm font-semibold text-[#4f46e5]">Operations Manager</p>
              <h2 className="mt-2 font-display text-2xl font-bold tracking-tight text-[#131b2e]">
                {isRegistration ? "Create your account" : "Welcome back"}
              </h2>
              <p className="mt-2 text-sm text-[#777587]">
                {isRegistration
                  ? "Set up your secure RosterIQ manager account."
                  : "Log in with your work email and password."}
              </p>

              <form className="mt-7 space-y-4" onSubmit={handleSubmit}>
                {isRegistration && (
                  <label className="block text-sm font-medium text-[#283044]">
                    Full Name
                    <input
                      autoComplete="name"
                      className="mt-1.5 h-11 w-full rounded-xl border border-[#dfe1ec] px-3 text-sm outline-none transition focus:border-[#4f46e5]"
                      name="fullName"
                      required
                      type="text"
                    />
                  </label>
                )}
                <label className="block text-sm font-medium text-[#283044]">
                  Email
                  <input
                    autoComplete="email"
                    className="mt-1.5 h-11 w-full rounded-xl border border-[#dfe1ec] px-3 text-sm outline-none transition focus:border-[#4f46e5]"
                    name="email"
                    placeholder="manager@work.com"
                    required
                    type="email"
                  />
                </label>
                <label className="block text-sm font-medium text-[#283044]">
                  Password
                  <input
                    autoComplete="current-password"
                    className="mt-1.5 h-11 w-full rounded-xl border border-[#dfe1ec] px-3 text-sm outline-none transition focus:border-[#4f46e5]"
                    minLength={8}
                    name="password"
                    required
                    type="password"
                  />
                </label>
                {isRegistration && (
                  <label className="block text-sm font-medium text-[#283044]">
                    Confirm Password
                    <input
                      autoComplete="new-password"
                      className="mt-1.5 h-11 w-full rounded-xl border border-[#dfe1ec] px-3 text-sm outline-none transition focus:border-[#4f46e5]"
                      minLength={8}
                      name="confirmPassword"
                      required
                      type="password"
                    />
                  </label>
                )}
                {errorMessage && (
                  <p
                    aria-live="polite"
                    className="rounded-xl bg-[#fff0ef] px-3 py-2.5 text-sm text-[#a21b1b]"
                    role="alert"
                  >
                    {errorMessage}
                  </p>
                )}
                {noticeMessage && (
                  <p
                    aria-live="polite"
                    className="rounded-xl bg-[#eefbf5] px-3 py-2.5 text-sm text-[#176b45]"
                    role="status"
                  >
                    {noticeMessage}
                  </p>
                )}
                <button
                  className="flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-[#4f46e5] px-4 text-sm font-semibold text-white transition-colors hover:bg-[#3525cd] disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={pending || !client}
                  type="submit"
                >
                  {pending && <LoaderCircle aria-hidden="true" className="h-4 w-4 animate-spin" />}
                  {pending
                    ? "Please wait..."
                    : isRegistration
                      ? "Create Account"
                      : "Log in"}
                </button>
              </form>
              <p className="mt-6 text-center text-sm text-[#777587]">
                {isRegistration ? "Already registered?" : "New to RosterIQ?"}{" "}
                <button
                  type="button"
                  onClick={() => changeMode(isRegistration ? "login" : "register")}
                  className="font-semibold text-[#4f46e5] hover:text-[#3525cd]"
                >
                  {isRegistration ? "Log in" : "Create Account"}
                </button>
              </p>
            </>
          )}

          {!client && (
            <p className="mt-6 rounded-xl bg-[#fff7e6] px-3 py-2.5 text-xs leading-5 text-[#76500c]">
              Supabase is not configured. Add the project URL and public anon key to{" "}
              <code>frontend/.env.local</code>, then restart the frontend.
            </p>
          )}
          <p className="mt-8 border-t border-[#eff0f6] pt-5 text-center text-xs text-[#8a8998]">
            Secure access for your Operations Manager account
          </p>
        </section>
      </div>
    </main>
  );
}
