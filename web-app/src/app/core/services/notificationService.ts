import { Injectable } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';

@Injectable({ providedIn: 'root' })
export class NotificationService {
  constructor(private snackBar: MatSnackBar) {}

  showError(message: string) {
    this.snackBar.open(message, 'Close', {
      duration: 5000,
      panelClass: ['error-snackbar'],
    });
  }

    showMessage(message:string, duration: number = 5000) {
      this.snackBar.open(message, 'Close', {
        duration: duration,
        panelClass: ['message-snackbar'],
      });
    }
}
