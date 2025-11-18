import { Component } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';
import { MatToolbar } from '@angular/material/toolbar';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, MatToolbar, MatIconModule, RouterLink],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
}
