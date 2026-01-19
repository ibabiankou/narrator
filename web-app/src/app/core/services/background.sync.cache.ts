import { ConnectionService } from './connection.service';
import { catchError, EMPTY, firstValueFrom, forkJoin, map, Observable, switchMap, tap } from 'rxjs';
import { fromPromise } from 'rxjs/internal/observable/innerFrom';

// TODO: Limit number of sync attempts.
interface Entry<T> {
  url: string;
  value: T;
  syncWhenOnline: boolean;
}

/**
 * A function that loads an entry to be cached from its source (typically backend).
 */
type EntryLoader<T> = (key: string) => Observable<T>;

/**
 * A function that writes(syncs) an entry back to its source (typically backend).
 */
type EntryWriter<T> = (key: string, value: T) => Observable<void>;

const DUMMY_WRITER: EntryWriter<any> = () => EMPTY;

/**
 * A cache that stores write requests when offline and retries them once online.
 */
export class BackgroundSyncCache<T> {
  private isOnline: boolean = false;
  private readonly load: EntryLoader<T>;
  private readonly sync: EntryWriter<T>;

  constructor(private connectionService: ConnectionService,
              private storeName: string,
              loader: EntryLoader<T>,
              _sync?: EntryWriter<T> | undefined) {
    this.load = loader;
    this.sync = _sync ? _sync : DUMMY_WRITER;

    this.connectionService.$isOnline.subscribe(online => {
      const needToSync = !this.isOnline && online;
      this.isOnline = online;

      if (needToSync) {
        this.getAllEntries().then(entries => {
          const syncEntries = entries.filter(entry => entry.syncWhenOnline);

          if (syncEntries.length === 0) {
            return;
          }

          const observables: Observable<void>[] = [];
          for (const entry of syncEntries) {
            observables.push(this.sync(entry.url, entry.value).pipe(
              tap(() => this._set({url: entry.url, value: entry.value, syncWhenOnline: false})),
            ));
          }

          return firstValueFrom(forkJoin(observables));
        }).catch(reason => console.warn("Failed to sync some entries:", reason));
      }
    });
  }

  private async getDB(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.storeName, 1);
      let store: IDBObjectStore;

      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains(this.storeName)) {
          store = db.createObjectStore(this.storeName, {keyPath: 'url'});
        } else {
          store = request.transaction!.objectStore(this.storeName);
        }
      };

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Stores value in the cache with a flag if sync is needed when online.
   */
  private async _set(entry: Entry<T>): Promise<void> {
    const db = await this.getDB();
    const tx = db.transaction(this.storeName, 'readwrite');
    tx.objectStore(this.storeName).put(entry);
    return new Promise((res) => (tx.oncomplete = () => res()));
  }

  set(key: string, value: T): Observable<void> {
    if (!this.isOnline) {
      return fromPromise(this._set({url: key, value: value, syncWhenOnline: true}));
    }

    return this.sync(key, value).pipe(
      switchMap(() => {
        return fromPromise(this._set({url: key, value: value, syncWhenOnline: false}));
      }),
      catchError((err) => {
        console.warn('Sync has failed, marking for background sync', err);
        return fromPromise(this._set({url: key, value: value, syncWhenOnline: true}));
      })
    );
  }

  /**
   * Loads value from the cache.
   */
  private async _get(key: string): Promise<Entry<T> | undefined> {
    const db = await this.getDB();
    const tx = db.transaction(this.storeName, 'readonly');
    const request = tx.objectStore(this.storeName).get(key);
    return new Promise((res) => (request.onsuccess = () => res(request.result)));
  }

  get(key: string): Observable<T | undefined> {
    if (!this.isOnline) {
      return fromPromise(this._get(key)).pipe(map(v => v?.value));
    }

    return this.load(key).pipe(
      tap((val) => this._set({url: key, value: val, syncWhenOnline: false})),
      catchError((error) => {
        console.warn("Loader has failed, falling back to cache:", error);
        return fromPromise(this._get(key)).pipe(map(v => v?.value));
      }));
  }

  private async getAllEntries(): Promise<Entry<T>[]> {
    const db = await this.getDB();
    const tx = db.transaction(this.storeName, 'readonly');
    const store = tx.objectStore(this.storeName);
    const request = store.getAll();
    return new Promise((resolve, reject) => {
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  getAll(): Observable<T[]> {
    return fromPromise(this.getAllEntries()).pipe(
      map(entries => entries.map(entry => entry.value))
    );
  }
}
