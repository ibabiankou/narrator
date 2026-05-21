import { Component, input } from '@angular/core';
import { BreadcrumbContentDirective, ToolbarComponent } from '../../components/toolbar/toolbar.component';

@Component({
  selector: 'app-view-readium',
  imports: [
    ToolbarComponent,
    BreadcrumbContentDirective,
  ],
  templateUrl: './view-readium.html',
  styleUrl: './view-readium.scss',
})
export class ViewReadium {
  file = input.required<string>();
}
