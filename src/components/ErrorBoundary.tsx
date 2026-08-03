import React, { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-screen w-full flex-col items-center justify-center bg-[#0c1520] p-6 text-white">
          <h1 className="mb-4 text-2xl font-bold text-red-500">Kutilmagan xatolik yuz berdi</h1>
          <div className="mb-6 rounded-lg bg-red-500/10 p-4 text-sm text-red-400 max-w-lg overflow-auto">
            {this.state.error?.message || "Noma'lum xato"}
          </div>
          <button
            onClick={() => {
              // Hard refresh to clear caches if it's a chunk error
              window.location.reload();
            }}
            className="rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white transition-all hover:bg-blue-700 active:scale-95"
          >
            Sahifani yangilash
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
