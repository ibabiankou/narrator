import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-skeleton',
  standalone: true,
  template: `
    <div [style.width]="width" [style.min-width]="minWidth" [style.height]="height" class="skeleton"></div>`,
  styles: [`
    :host {
      display: block;
    }
    .skeleton {
      background: lightgray;
      animation: pulse 1s infinite;
      border-radius: 4px;
    }
    @keyframes pulse {
      50% {
        opacity: .35;
      }
    }
  `]
})
export class SkeletonComponent {
  @Input() width = '100%';
  @Input() minWidth = '100px';
  @Input() height = '100%';
}
