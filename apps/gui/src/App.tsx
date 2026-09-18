import { Toaster } from "sonner";

import { AppShell } from "@/components/AppShell";

export default function App() {
  return (
    <>
      <AppShell />
      <Toaster
        theme="light"
        closeButton
        position="top-center"
        offset={{ top: "calc(var(--shell-topbar-h) + 8px)" }}
      />
    </>
  );
}
