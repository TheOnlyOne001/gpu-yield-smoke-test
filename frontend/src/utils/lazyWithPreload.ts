import dynamic from 'next/dynamic';
import { ComponentType } from 'react';

// Current issue: TypeScript errors because it's .ts not .tsx
// Fix: Either use simple version or rename to .tsx

// Option 1: Keep as .ts with simple version
export function lazyWithPreload<T extends ComponentType<any>>(
  factory: () => Promise<{ default: T }>,
) {
  const Component = dynamic(factory, {
    loading: () => null,
    ssr: true,
  });

  (Component as any).preload = factory;
  return Component;
}

// Option 2: Rename to .tsx and use JSX loading

// Usage example:
// const HeavyComponent = lazyWithPreload(() => import('./HeavyComponent'));

// Preload when needed:
// HeavyComponent.preload();