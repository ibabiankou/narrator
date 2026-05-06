import { inject, Injectable } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';

@Injectable({providedIn: 'root'})
export class NotificationService {
  private snackBar: MatSnackBar = inject(MatSnackBar);

  showError(message: string) {
    this.snackBar.open(message, 'Close', {
      duration: 5000,
      panelClass: ['error-snackbar'],
    });
  }

  showMessage(message: string, duration: number = 5000) {
    this.snackBar.open(message, 'Close', {
      duration: duration,
      panelClass: ['message-snackbar'],
    });
  }

  dismiss() {
    this.snackBar.dismiss();
  }
}
