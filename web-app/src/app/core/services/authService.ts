import { Injectable, inject } from '@angular/core';
import { interval } from 'rxjs';
import Keycloak from 'keycloak-js';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private keycloak = inject(Keycloak);

  constructor() {
    const heartbeatInterval = 55_000;
    interval(heartbeatInterval*2).subscribe(async () => {
      try {
        await this.keycloak.updateToken(heartbeatInterval*1.5).then(function(refreshed) {
          if (refreshed) {
            console.debug('Token was successfully refreshed');
          }
        }).catch(function() {
          console.error('Failed to refresh the token, or the session has expired');
        });
      } catch (error) {
        console.error('Failed to refresh token during heartbeat', error);
      }
    });
  }

  isOwner(ownerId: string): boolean {
    if (this.keycloak.tokenParsed) {
      return this.keycloak.tokenParsed.sub === ownerId;
    }
    return false;
  }
}
