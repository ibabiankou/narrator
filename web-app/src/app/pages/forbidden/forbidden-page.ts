import { Component } from '@angular/core';
import { ToolbarComponent } from '../../components/toolbar/toolbar.component';

@Component({
  selector: 'app-forbidden-page',
  imports: [
    ToolbarComponent,
  ],
  templateUrl: './forbidden-page.html',
  styleUrl: './forbidden-page.scss',
})
export class ForbiddenPage {
}
