import { Toaster } from "sonner";

import { AppShell } from "@/components/AppShell";
import { StartupSplash } from "@/components/StartupSplash";

export default function App() {
  return (
    <>
      <AppShell />
      <StartupSplash />
      <Toaster
        richColors
        closeButton
        position="top-center"
        offset={{ top: "calc(var(--shell-topbar-h) + 8px)" }}
      />
    </>
  );
}
