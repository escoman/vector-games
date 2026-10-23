; Данные: data_glyph_ptr_table
; Адрес: 0x0600
; Размер: 512 байт (256 слов)
; Tier 2: word[g] = data_glyph_block + OFF(g), бит0 = ТЕГ compact (1 = одно-
;   плоскостная 8Б-маска; 0 = сырой 32Б). func_render_glyph читает слово в DE,
;   тестирует bit0 и снимает его (AND 0xFEh) для адреса записи.

data_glyph_ptr_table:
    ; глифы 0..7
    DEFW data_glyph_block+1        , data_glyph_block+9        , data_glyph_block+16       , data_glyph_block+48       
    DEFW data_glyph_block+80       , data_glyph_block+112      , data_glyph_block+144      , data_glyph_block+176      
    ; глифы 8..15
    DEFW data_glyph_block+208      , data_glyph_block+240      , data_glyph_block+272      , data_glyph_block+304      
    DEFW data_glyph_block+336      , data_glyph_block+368      , data_glyph_block+400      , data_glyph_block+432      
    ; глифы 16..23
    DEFW data_glyph_block+464      , data_glyph_block+496      , data_glyph_block+528      , data_glyph_block+560      
    DEFW data_glyph_block+592      , data_glyph_block+624      , data_glyph_block+4384     , data_glyph_block+4416     ; 22,23 <- art 188,189 (светлый выход)
    ; глифы 24..31
    DEFW data_glyph_block+4448     , data_glyph_block+4480     , data_glyph_block+784      , data_glyph_block+816      ; 24,25 <- art 190,191 (светлый выход)
    DEFW data_glyph_block+848      , data_glyph_block+880      , data_glyph_block+913      , data_glyph_block+921      
    ; глифы 32..39
    DEFW data_glyph_block+929      , data_glyph_block+937      , data_glyph_block+945      , data_glyph_block+953      
    DEFW data_glyph_block+961      , data_glyph_block+969      , data_glyph_block+977      , data_glyph_block+985      
    ; глифы 40..47
    DEFW data_glyph_block+993      , data_glyph_block+1001     , data_glyph_block+1009     , data_glyph_block+1017     
    DEFW data_glyph_block+1025     , data_glyph_block+1033     , data_glyph_block+1041     , data_glyph_block+1049     
    ; глифы 48..55
    DEFW data_glyph_block+1057     , data_glyph_block+1065     , data_glyph_block+1073     , data_glyph_block+1081     
    DEFW data_glyph_block+1089     , data_glyph_block+1097     , data_glyph_block+1105     , data_glyph_block+1113     
    ; глифы 56..63
    DEFW data_glyph_block+1121     , data_glyph_block+1129     , data_glyph_block+1137     , data_glyph_block+1145     
    DEFW data_glyph_block+1153     , data_glyph_block+1161     , data_glyph_block+1169     , data_glyph_block+1177     
    ; глифы 64..71
    DEFW data_glyph_block+1185     , data_glyph_block+1193     , data_glyph_block+1201     , data_glyph_block+1209     
    DEFW data_glyph_block+1217     , data_glyph_block+1225     , data_glyph_block+1233     , data_glyph_block+1241     
    ; глифы 72..79
    DEFW data_glyph_block+1249     , data_glyph_block+1257     , data_glyph_block+1265     , data_glyph_block+1273     
    DEFW data_glyph_block+1281     , data_glyph_block+1289     , data_glyph_block+1297     , data_glyph_block+1305     
    ; глифы 80..87
    DEFW data_glyph_block+1313     , data_glyph_block+1321     , data_glyph_block+1329     , data_glyph_block+1337     
    DEFW data_glyph_block+1345     , data_glyph_block+1353     , data_glyph_block+1361     , data_glyph_block+1369     
    ; глифы 88..95
    DEFW data_glyph_block+1377     , data_glyph_block+1385     , data_glyph_block+1393     , data_glyph_block+1401     
    DEFW data_glyph_block+1409     , data_glyph_block+1417     , data_glyph_block+1425     , data_glyph_block+1433     
    ; глифы 96..103
    DEFW data_glyph_block+1440     , data_glyph_block+1472     , data_glyph_block+1504     , data_glyph_block+1536     
    DEFW data_glyph_block+1568     , data_glyph_block+1600     , data_glyph_block+1632     , data_glyph_block+1664     
    ; глифы 104..111
    DEFW data_glyph_block+1696     , data_glyph_block+1728     , data_glyph_block+1760     , data_glyph_block+1792     
    DEFW data_glyph_block+1824     , data_glyph_block+1856     , data_glyph_block+1888     , data_glyph_block+1920     
    ; глифы 112..119
    DEFW data_glyph_block+1952     , data_glyph_block+1984     , data_glyph_block+2016     , data_glyph_block+2048     
    DEFW data_glyph_block+2080     , data_glyph_block+2112     , data_glyph_block+2144     , data_glyph_block+2176     
    ; глифы 120..127
    DEFW data_glyph_block+2208     , data_glyph_block+2240     , data_glyph_block+2272     , data_glyph_block+2304     
    DEFW data_glyph_block+2336     , data_glyph_block+2368     , data_glyph_block+2400     , data_glyph_block+2432     
    ; глифы 128..135
    DEFW data_glyph_block+2464     , data_glyph_block+2496     , data_glyph_block+2528     , data_glyph_block+2560     
    DEFW data_glyph_block+2592     , data_glyph_block+2624     , data_glyph_block+2656     , data_glyph_block+2688     
    ; глифы 136..143
    DEFW data_glyph_block+2720     , data_glyph_block+2752     , data_glyph_block+2784     , data_glyph_block+2816     
    DEFW data_glyph_block+2848     , data_glyph_block+2880     , data_glyph_block+2912     , data_glyph_block+2944     
    ; глифы 144..151
    DEFW data_glyph_block+2976     , data_glyph_block+3008     , data_glyph_block+3040     , data_glyph_block+3072     
    DEFW data_glyph_block+3104     , data_glyph_block+3136     , data_glyph_block+3168     , data_glyph_block+3200     
    ; глифы 152..159
    DEFW data_glyph_block+3232     , data_glyph_block+3264     , data_glyph_block+3296     , data_glyph_block+3328     
    DEFW data_glyph_block+3360     , data_glyph_block+3392     , data_glyph_block+3424     , data_glyph_block+3456     
    ; глифы 160..167
    DEFW data_glyph_block+3488     , data_glyph_block+3520     , data_glyph_block+3552     , data_glyph_block+3584     
    DEFW data_glyph_block+3616     , data_glyph_block+3648     , data_glyph_block+3680     , data_glyph_block+3712     
    ; глифы 168..175
    DEFW data_glyph_block+3744     , data_glyph_block+3776     , data_glyph_block+3808     , data_glyph_block+3840     
    DEFW data_glyph_block+3872     , data_glyph_block+3904     , data_glyph_block+3936     , data_glyph_block+3968     
    ; глифы 176..183
    DEFW data_glyph_block+4000     , data_glyph_block+4032     , data_glyph_block+4064     , data_glyph_block+4096     
    DEFW data_glyph_block+4128     , data_glyph_block+4160     , data_glyph_block+4192     , data_glyph_block+4224     
    ; глифы 184..191
    DEFW data_glyph_block+4256     , data_glyph_block+4288     , data_glyph_block+4320     , data_glyph_block+4352     
    DEFW data_glyph_block+4384     , data_glyph_block+4416     , data_glyph_block+4448     , data_glyph_block+4480     
    ; глифы 192..199
    DEFW data_glyph_block+4513     , data_glyph_block+4521     , data_glyph_block+4529     , data_glyph_block+4537     
    DEFW data_glyph_block+4545     , data_glyph_block+4553     , data_glyph_block+4561     , data_glyph_block+4569     
    ; глифы 200..207
    DEFW data_glyph_block+4577     , data_glyph_block+4585     , data_glyph_block+4593     , data_glyph_block+4601     
    DEFW data_glyph_block+4609     , data_glyph_block+4617     , data_glyph_block+4625     , data_glyph_block+4633     
    ; глифы 208..215
    DEFW data_glyph_block+4641     , data_glyph_block+4649     , data_glyph_block+4657     , data_glyph_block+4665     
    DEFW data_glyph_block+4673     , data_glyph_block+4681     , data_glyph_block+4689     , data_glyph_block+4697     
    ; глифы 216..223
    DEFW data_glyph_block+4705     , data_glyph_block+4713     , data_glyph_block+4721     , data_glyph_block+4729     
    DEFW data_glyph_block+4737     , data_glyph_block+4745     , data_glyph_block+4753     , data_glyph_block+4761     
    ; глифы 224..231
    DEFW data_glyph_block+4769     , data_glyph_block+4777     , data_glyph_block+4785     , data_glyph_block+4793     
    DEFW data_glyph_block+4801     , data_glyph_block+4809     , data_glyph_block+4817     , data_glyph_block+4825     
    ; глифы 232..239
    DEFW data_glyph_block+4833     , data_glyph_block+4841     , data_glyph_block+4849     , data_glyph_block+4857     
    DEFW data_glyph_block+4865     , data_glyph_block+4873     , data_glyph_block+4881     , data_glyph_block+4889     
    ; глифы 240..247
    DEFW data_glyph_block+4897     , data_glyph_block+4905     , data_glyph_block+4913     , data_glyph_block+4921     
    DEFW data_glyph_block+4929     , data_glyph_block+4937     , data_glyph_block+4945     , data_glyph_block+4953     
    ; глифы 248..255
    DEFW data_glyph_block+4961     , data_glyph_block+4969     , data_glyph_block+4977     , data_glyph_block+4985     
    DEFW data_glyph_block+4993     , data_glyph_block+5001     , data_glyph_block+5008     , data_glyph_block+5041     
