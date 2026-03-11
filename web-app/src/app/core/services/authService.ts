import { Injectable, inject } from '@angular/core';
import { interval } from 'rxjs';
import Keycloak from 'keycloak-js';

@Injectable({ providedIn: 'root' })
export class AuthHeartbeatService {
  private keycloak = inject(Keycloak);

  constructor() {
    const heartbeatInterval = 55_000;
    interval(heartbeatInterval*2).subscribe(async () => {
      try {
        const kc = this.keycloak;
        await this.keycloak.updateToken(heartbeatInterval*1.5).then(function(refreshed) {
          if (refreshed) {
            console.debug('Token was successfully refreshed');
            console.debug(kc.tokenParsed);
          } else {
            console.debug('Token is still valid');
          }
        }).catch(function() {
          console.error('Failed to refresh the token, or the session has expired');
        });
      } catch (error) {
        console.error('Failed to refresh token during heartbeat', error);
      }
    });
  }
}
