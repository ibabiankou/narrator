import { Component, Injector } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { MatIconModule, MatIconRegistry } from '@angular/material/icon';
import { OSBindingsService } from './components/player/os-binding.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, MatIconModule],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  constructor(iconRegistry: MatIconRegistry, injector: Injector) {
    iconRegistry.setDefaultFontSetClass('material-symbols-outlined');
    injector.get(OSBindingsService);
  }
}
