import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "@/App";
import "@/styles/globals.css";
import "@/styles/app-shell.css";

// 桌面壳内禁用 WebView 默认右键菜单（非产品功能）
document.addEventListener("contextmenu", (event) => {
  event.preventDefault();
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
