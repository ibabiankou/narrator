import { Component } from '@angular/core';
import { BreadcrumbContentDirective, ToolbarComponent } from '../../components/toolbar/toolbar.component';

@Component({
  selector: 'app-edit-metadata-page',
  imports: [
    ToolbarComponent,
    BreadcrumbContentDirective
  ],
  templateUrl: './edit-metadata-page.html',
  styleUrl: './edit-metadata-page.scss',
})
export class EditMetadataPage {

}
