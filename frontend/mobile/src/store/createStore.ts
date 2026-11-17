import { useSyncExternalStore } from "react";

type SetState<T> = (partial: Partial<T> | ((state: T) => Partial<T>)) => void;
type GetState<T> = () => T;
type Listener<T> = (state: T, prev: T) => void;

export type StoreApi<T> = {
  getState: GetState<T>;
  setState: SetState<T>;
  subscribe: (listener: Listener<T>) => () => void;
};

type Hook<T> = {
  <U>(selector: (state: T) => U): U;
  (): T;
  getState: GetState<T>;
  setState: SetState<T>;
  subscribe: (listener: Listener<T>) => () => void;
};

/**
 * 轻量 store（兼容 zustand 用法），避免 Taro 小程序把 zustand.create 错绑到 React。
 */
export function createStore<T extends object>(
  initializer: (set: SetState<T>, get: GetState<T>) => T
): Hook<T> {
  let state: T;
  const listeners = new Set<Listener<T>>();

  const getState: GetState<T> = () => state;
  const setState: SetState<T> = (partial) => {
    const next = typeof partial === "function" ? partial(state) : partial;
    if (Object.is(next, state)) return;
    const prev = state;
    state = Object.assign({}, state, next);
    listeners.forEach((l) => l(state, prev));
  };
  const subscribe = (listener: Listener<T>) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
  };

  state = initializer(setState, getState);

  function useStore(): T;
  function useStore<U>(selector: (s: T) => U): U;
  function useStore<U>(selector?: (s: T) => U) {
    return useSyncExternalStore(
      subscribe,
      () => (selector ? selector(getState()) : getState()) as U & T,
      () => (selector ? selector(getState()) : getState()) as U & T
    );
  }

  useStore.getState = getState;
  useStore.setState = setState;
  useStore.subscribe = subscribe;
  return useStore;
}
