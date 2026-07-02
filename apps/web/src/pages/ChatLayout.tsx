import { Outlet } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import ThemeToggle from "../components/ThemeToggle";

export default function ChatLayout() {
  return (
    <div className="flex h-screen bg-white dark:bg-gray-900">
      <Sidebar />
      <main className="flex flex-1 flex-col">
        <header className="flex items-center justify-end border-b border-gray-200 px-4 py-2 dark:border-gray-700">
          <ThemeToggle />
        </header>
        <div className="flex flex-1 flex-col">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
