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
    ServiceLocator.injector = injector;

    // this.checkStorage().catch(err => console.error(err));
  }

  // TODO: Collect this info and show on some kind of info page.
  // async checkStorage() {
  //   if (navigator.storage && navigator.storage.estimate) {
  //     const { quota, usage } = await navigator.storage.estimate();
  //
  //     const quotaNum = quota ? quota : 0;
  //     if (quotaNum === 0)
  //       console.log("Quota is unknown...");
  //     else
  //       console.log("Quota is %sB", quotaNum);
  //
  //     const usageNum = usage ? usage : 0;
  //     if (usageNum === 0)
  //       console.log("Usage is unknown.");
  //     else
  //       console.log("Usage is %sB", usageNum);
  //
  //     if (quotaNum > 0 && usageNum > 0) {
  //       const percentageUsed = quotaNum > 0 ? ((usageNum / quotaNum) * 100) : 0;
  //       const remainingMB = (quotaNum - usageNum) / (1024 * 1024);
  //
  //       console.log(`Used: ${percentageUsed.toFixed(2)}%`);
  //       console.log(`Remaining: ${remainingMB.toFixed(0)} MB`);
  //     }
  //   }
  // }
}

export class ServiceLocator {
  static injector: Injector;
}
