import { Injectable } from '@angular/core';
import { fromEvent, map, merge, Observable, shareReplay, startWith } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ConnectionService {
  readonly $isOnline: Observable<boolean>;

  constructor() {
    this.$isOnline = merge(
      fromEvent(window, 'online').pipe(map(() => true)),
      fromEvent(window, 'offline').pipe(map(() => false))
    ).pipe(
      startWith(navigator.onLine),
      shareReplay(1)
    );
  }
}
