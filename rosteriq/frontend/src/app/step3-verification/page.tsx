"use client";

import { useState } from "react";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";

const storageKey = "rosteriq-step3-verification";

type TestIds = {
  organizationId: string;
  managerId: string;
  brandId?: string;
  processId?: string;
  podId?: string;
  employeeId?: string;
};

function readTestIds(): TestIds | null {
  const saved = window.localStorage.getItem(storageKey);
  if (!saved) return null;

  const parsed: unknown = JSON.parse(saved);
  if (
    typeof parsed !== "object" ||
    parsed === null ||
    !("organizationId" in parsed) ||
    typeof parsed.organizationId !== "string" ||
    !("managerId" in parsed) ||
    typeof parsed.managerId !== "string"
  ) {
    throw new Error("Stored verification state is invalid.");
  }
  return parsed as TestIds;
}

function saveTestIds(ids: TestIds) {
  window.localStorage.setItem(storageKey, JSON.stringify(ids));
}

export default function Step3CheckPage() {
  const [output, setOutput] = useState("Ready. Use the manager session first.");
  const [busy, setBusy] = useState(false);

  async function runManagerChecks() {
    const client = getSupabaseBrowserClient();
    if (!client) throw new Error("Supabase browser client is not configured.");
    if (readTestIds()) throw new Error("A verification organization already exists; run cleanup first.");

    const { data: userData, error: userError } = await client.auth.getUser();
    if (userError) throw userError;
    if (!userData.user) throw new Error("An authenticated manager session is required.");
    const managerId = userData.user.id;

    const suffix = crypto.randomUUID();
    const { data: organizations, error: createError } = await client.rpc("create_organization", {
      organization_name: `RosterIQ temporary Step 3 check ${suffix}`,
    });
    if (createError) throw createError;
    const organization = organizations?.[0];
    if (!organization) throw new Error("create_organization returned no organization.");

    let ids: TestIds = { organizationId: organization.id, managerId };
    saveTestIds(ids);
    const passed = [
      "Authenticated create_organization RPC returned one organization.",
    ];

    const { data: visibleOrganization, error: organizationError } = await client
      .from("organizations")
      .select("id, name")
      .eq("id", organization.id)
      .maybeSingle();
    if (organizationError) throw organizationError;
    if (!visibleOrganization || visibleOrganization.name !== organization.name) {
      throw new Error("The manager could not read the created organization.");
    }
    passed.push("The manager can read the created organization.");

    const { data: membership, error: membershipError } = await client
      .from("organization_members")
      .select("id")
      .eq("organization_id", organization.id)
      .eq("manager_id", managerId)
      .maybeSingle();
    if (membershipError) throw membershipError;
    if (!membership) throw new Error("The creator's organization membership was not created.");
    passed.push("The manager membership was created.");

    const brandName = `Temporary ${suffix}`;
    const { data: brand, error: brandInsertError } = await client
      .from("brands")
      .insert({ organization_id: organization.id, name: brandName })
      .select("id")
      .single();
    if (brandInsertError) throw brandInsertError;
    ids = { ...ids, brandId: brand.id };
    saveTestIds(ids);
    const { data: brandRelation, error: brandRelationError } = await client
      .from("brands")
      .select("id, organization:organizations!brands_organization_id_fkey(id)")
      .eq("id", brand.id)
      .single();
    if (brandRelationError) throw brandRelationError;
    if (!brandRelation.organization || brandRelation.organization.id !== organization.id) {
      throw new Error("Brand-to-organization foreign key relationship did not resolve.");
    }
    passed.push("Brand organization foreign key resolves.");

    const { data: process, error: processInsertError } = await client
      .from("processes")
      .insert({ brand_id: brand.id, name: `Temporary process ${suffix}` })
      .select("id")
      .single();
    if (processInsertError) throw processInsertError;
    ids = { ...ids, processId: process.id };
    saveTestIds(ids);
    const { data: processRelation, error: processRelationError } = await client
      .from("processes")
      .select("id, brand:brands!processes_brand_id_fkey(id)")
      .eq("id", process.id)
      .single();
    if (processRelationError) throw processRelationError;
    if (!processRelation.brand || processRelation.brand.id !== brand.id) {
      throw new Error("Process-to-brand foreign key relationship did not resolve.");
    }
    passed.push("Process-to-brand foreign key resolves.");

    const { data: pod, error: podInsertError } = await client
      .from("pods")
      .insert({ process_id: process.id, name: `Temporary pod ${suffix}` })
      .select("id")
      .single();
    if (podInsertError) throw podInsertError;
    ids = { ...ids, podId: pod.id };
    saveTestIds(ids);
    const { data: podRelation, error: podRelationError } = await client
      .from("pods")
      .select("id, process:processes!pods_process_id_fkey(id)")
      .eq("id", pod.id)
      .single();
    if (podRelationError) throw podRelationError;
    if (!podRelation.process || podRelation.process.id !== process.id) {
      throw new Error("Pod-to-process foreign key relationship did not resolve.");
    }
    passed.push("Pod-to-process foreign key resolves.");

    const { data: employee, error: employeeInsertError } = await client
      .from("employees")
      .insert({
        organization_id: organization.id,
        employee_code: `VERIFY-${suffix}`,
        first_name: "Temporary",
        last_name: "RosterIQ",
        email: `verify-${suffix}@example.invalid`,
        designation: "Temporary verification",
        status: "active",
      })
      .select("id")
      .single();
    if (employeeInsertError) throw employeeInsertError;
    ids = { ...ids, employeeId: employee.id };
    saveTestIds(ids);
    const { data: employeeRelation, error: employeeRelationError } = await client
      .from("employees")
      .select("id, organization:organizations!employees_organization_id_fkey(id)")
      .eq("id", employee.id)
      .single();
    if (employeeRelationError) throw employeeRelationError;
    if (!employeeRelation.organization || employeeRelation.organization.id !== organization.id) {
      throw new Error("Employee-to-organization foreign key relationship did not resolve.");
    }
    passed.push("Employee organization foreign key resolves.");

    return `Organization ID: ${organization.id}\n${passed.map((item) => `PASS: ${item}`).join("\n")}\nSwitch to an existing unrelated account and run its access check.`;
  }

  async function runUnrelatedUserChecks() {
    const client = getSupabaseBrowserClient();
    if (!client) throw new Error("Supabase browser client is not configured.");
    const ids = readTestIds();
    if (!ids) throw new Error("No saved verification organization exists.");

    const { data: userData, error: userError } = await client.auth.getUser();
    if (userError) throw userError;
    if (!userData.user) throw new Error("An authenticated user session is required.");
    if (userData.user.id === ids.managerId) {
      throw new Error("This is the organization owner; sign in using the unrelated existing account.");
    }

    const checks: [string, { data: { id: string } | null; error: { message: string } | null }][] = [];
    checks.push(["organization", await client.from("organizations").select("id").eq("id", ids.organizationId).maybeSingle()]);
    checks.push(["organization membership", await client.from("organization_members").select("id").eq("organization_id", ids.organizationId).eq("manager_id", ids.managerId).maybeSingle()]);
    if (ids.brandId) checks.push(["brand", await client.from("brands").select("id").eq("id", ids.brandId).maybeSingle()]);
    if (ids.processId) checks.push(["process", await client.from("processes").select("id").eq("id", ids.processId).maybeSingle()]);
    if (ids.podId) checks.push(["pod", await client.from("pods").select("id").eq("id", ids.podId).maybeSingle()]);
    if (ids.employeeId) checks.push(["employee", await client.from("employees").select("id").eq("id", ids.employeeId).maybeSingle()]);

    const passed: string[] = [];
    for (const [label, result] of checks) {
      if (result.error) throw new Error(`RLS query for ${label} failed: ${result.error.message}`);
      if (result.data) throw new Error(`Unrelated user could access the verification ${label}.`);
      passed.push(`PASS: RLS hides the ${label} from the unrelated user.`);
    }
    return passed.join("\n");
  }

  async function cleanup() {
    const client = getSupabaseBrowserClient();
    if (!client) throw new Error("Supabase browser client is not configured.");
    const ids = readTestIds();
    if (!ids) throw new Error("No saved verification organization exists.");
    const { data: userData, error: userError } = await client.auth.getUser();
    if (userError) throw userError;
    if (userData.user?.id !== ids.managerId) {
      throw new Error("Sign back in as the organization owner before cleanup.");
    }

    if (ids.employeeId) {
      const { error } = await client.from("employees").delete().eq("id", ids.employeeId);
      if (error) throw error;
    }
    if (ids.podId) {
      const { error } = await client.from("pods").delete().eq("id", ids.podId);
      if (error) throw error;
    }
    if (ids.processId) {
      const { error } = await client.from("processes").delete().eq("id", ids.processId);
      if (error) throw error;
    }
    if (ids.brandId) {
      const { error } = await client.from("brands").delete().eq("id", ids.brandId);
      if (error) throw error;
    }
    const { error: deleteOrganizationError } = await client
      .from("organizations")
      .delete()
      .eq("id", ids.organizationId);
    if (deleteOrganizationError) throw deleteOrganizationError;
    const { data: remaining, error: verifyDeleteError } = await client
      .from("organizations")
      .select("id")
      .eq("id", ids.organizationId)
      .maybeSingle();
    if (verifyDeleteError) throw verifyDeleteError;
    if (remaining) throw new Error("Verification organization remains after cleanup.");
    const { data: remainingMembership, error: verifyMembershipError } = await client
      .from("organization_members")
      .select("id")
      .eq("organization_id", ids.organizationId)
      .eq("manager_id", ids.managerId)
      .maybeSingle();
    if (verifyMembershipError) throw verifyMembershipError;
    if (remainingMembership) throw new Error("Verification membership remains after cleanup.");

    window.localStorage.removeItem(storageKey);
    return "PASS: temporary organization and verification rows were deleted.";
  }

  async function run(action: () => Promise<string>) {
    setBusy(true);
    try {
      setOutput(await action());
    } catch (error: unknown) {
      setOutput(`FAIL: ${error instanceof Error ? error.message : "Unexpected verification error."}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl space-y-4 p-8">
      <h1 className="text-2xl font-bold">Temporary Step 3 database verification</h1>
      <p>Uses the authenticated browser client only. Temporary database rows must be cleaned up before this page is removed.</p>
      <div className="flex flex-wrap gap-3">
        <button className="rounded bg-indigo-600 px-4 py-2 text-white disabled:opacity-50" disabled={busy} onClick={() => void run(runManagerChecks)}>Run manager checks</button>
        <button className="rounded bg-indigo-600 px-4 py-2 text-white disabled:opacity-50" disabled={busy} onClick={() => void run(runUnrelatedUserChecks)}>Check unrelated user</button>
        <button className="rounded bg-red-700 px-4 py-2 text-white disabled:opacity-50" disabled={busy} onClick={() => void run(cleanup)}>Clean up test data</button>
      </div>
      <pre className="whitespace-pre-wrap break-words rounded bg-slate-100 p-4 text-sm">{output}</pre>
    </main>
  );
}
