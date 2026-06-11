import { Navigate, Route, Routes } from "react-router-dom";
import { ClientAuthProvider } from "./ClientAuthContext";
import { ClientLoginPage } from "./ClientLoginPage";
import { ClientChatPage } from "./ClientChatPage";

export function ClientPortal() {
  return (
    <ClientAuthProvider>
      <Routes>
        <Route path="login" element={<ClientLoginPage />} />
        <Route path="chat" element={<ClientChatPage />} />
        <Route path="*" element={<Navigate to="/client/login" replace />} />
      </Routes>
    </ClientAuthProvider>
  );
}
