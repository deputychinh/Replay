import { createContext, useCallback, useContext, useState, type ReactNode } from 'react';
import './toast.css';

type Tone = 'success' | 'error' | 'info';
interface Item { id: number; message: string; tone: Tone }

const ToastContext = createContext<(message: string, tone?: Tone) => void>(() => {});
const DURATION_MS = 4000;
let nextId = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Item[]>([]);
  const show = useCallback((message: string, tone: Tone = 'success') => {
    const id = nextId++;
    setItems((list) => [...list, { id, message, tone }]);
    setTimeout(() => setItems((list) => list.filter((i) => i.id !== id)), DURATION_MS);
  }, []);
  return (
    <ToastContext.Provider value={show}>
      {children}
      <div className="toast" role="status" aria-live="polite">
        {items.map((item) => (
          <div key={item.id} className={`toast__item toast__item--${item.tone}`}>{item.message}</div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
