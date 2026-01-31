import { Injectable, Signal } from '@angular/core';
import { fromEvent, map, merge, Observable, shareReplay, startWith } from 'rxjs';
import { toSignal } from '@angular/core/rxjs-interop';

@Injectable({
  providedIn: 'root'
})
export class ConnectionService {
  readonly $isOnline: Observable<boolean>;
  readonly isOnline: Signal<boolean>;

  constructor() {
    this.$isOnline = merge(
      fromEvent(window, 'online').pipe(map(() => true)),
      fromEvent(window, 'offline').pipe(map(() => false))
    ).pipe(
      startWith(navigator.onLine),
      shareReplay(1)
    );
    this.isOnline = toSignal(this.$isOnline, {initialValue: navigator.onLine});
  }
}
