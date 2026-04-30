import { ChangeDetectionStrategy, Component } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule } from '@angular/material/dialog';

@Component({
  selector: 'app-shortcuts-dialog',
  templateUrl: './keyboardShortcuts.html',
  styleUrl: './keyboardShortcuts.scss',
  imports: [MatDialogModule, MatButtonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KeyboardShortcutsDialog {}
