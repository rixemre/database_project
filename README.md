# ⚔️ Bannerlord Wiki Veritabanı Projesi

Bu proje, **Mount & Blade II: Bannerlord** oyunundaki zengin dünyayı, karakterleri, krallıkları ve yerleşim yerlerini yapılandırılmış bir veritabanı (SQL) üzerinde modellemek amacıyla geliştirilmiştir. Oyunun sunduğu karmaşık ilişkileri (örneğin; lord-krallık bağlılıkları, şehirlerin üretim verileri) düzenli bir formatta sunmayı hedefler.

## 🚀 Proje Hakkında

Bannerlord'un dinamik yapısını bir "Wiki" mantığıyla veritabanına döken bu çalışma şunları içerir:
* **Karakter Yönetimi:** Hükümdarlar, lordlar ve yoldaşların verileri.
* **Krallık ve Kültürler:** Kalradya İmparatorluğu, Vlandiya, Kuzait gibi ana tarafların idari yapıları.
* **Ekonomi ve Yerleşim:** Şehirler, kaleler ve köylerin bağlılık ve üretim ilişkileri.
* **Teknik Altyapı:** İlişkisel veritabanı şemaları (ER Diyagramları) ve optimize edilmiş SQL tabloları.
* **Verilerin Toplanması:** Sitede kullanılan tüm veriler  ``` https://mountandblade.fandom.com/wiki/Mount%26Blade_II:_Bannerlord ```  adresinden scrape yöntemi kullanılarak çekilmiştir, bunun için gerekli repoya  ``` https://github.com/rixemre/Wiki-Scraper ``` bağlantısından ulaşabilirsiniz.

## 📂 Veritabanı Yapısı

Proje kapsamında oluşturulan temel tablolar ve içerikleri:

* **`Factions` (Taraflar):** Krallıkların isimleri, kültürleri ve hükümdar bilgileri.
* **`Heroes` (Kahramanlar):** Karakterlerin yetenekleri, yaşları ve aile bağları.
* **`Settlements` (Yerleşim Yerleri):** Şehirlerin refah seviyesi, garnizon kapasitesi ve üretim türleri.
* **`Troops` (Birlikler):** Askeri birimlerin ağaçları ve ekipman verileri.

## 🛠️ Kurulum ve Kullanım

1.  Bu depoyu bilgisayarınıza klonlayın:
    ```bash
    git clone [https://github.com/rixemre/Bannerlord-Wiki.git](https://github.com/rixemre/Bannerlord-Wiki.git)
    ```
2.  SQL dosyalarını tercih ettiğiniz bir veritabanı yönetim aracında çalıştırın.
3.  Tablolar arasındaki ilişkileri incelemek için hazırlanan ER diyagramlarını kullanabilirsiniz.

## 🛠️ Teknik Detaylar

Proje geliştirilirken aşağıdaki araçlar ve teknolojiler kullanılmıştır:
* **SQL:** Veri modelleme ve sorgulama süreçleri.
* **LaTeX:** Proje raporlaması ve teknik dokümantasyon.
* **Python:** Veri işleme ve otomasyon süreçleri için kullanılan scriptler.

## 🤝 Katkıda Bulunma

Hatalı bir veri fark ederseniz veya yeni bir tablo eklemek isterseniz, lütfen bir `Pull Request` gönderin veya bir `Issue` açın. Her türlü katkıya açığız!

---
