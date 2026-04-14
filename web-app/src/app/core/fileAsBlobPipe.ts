import { inject, Pipe, PipeTransform } from '@angular/core';
import { DomSanitizer, SafeUrl } from '@angular/platform-browser';
import { map, Observable } from 'rxjs';
import { FilesService } from './services/files.service';

@Pipe({
  name: 'fileAsBlob',
  standalone: true
})
export class FileAsBlobPipe implements PipeTransform {
  private filesService: FilesService = inject(FilesService);
  private sanitizer: DomSanitizer = inject(DomSanitizer);

  transform(url: string): Observable<SafeUrl> {
    return this.filesService.getFileData(url).pipe(
      map(fileData => {
        const buffer = fileData.data as ArrayBuffer;
        const blob = new Blob([buffer]);
        const objectUrl = URL.createObjectURL(blob);
        return this.sanitizer.bypassSecurityTrustUrl(objectUrl);
      })
    );
  }
}
