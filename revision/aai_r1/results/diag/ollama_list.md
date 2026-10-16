# ollama list (위성)

```
NAME                                                                       ID              SIZE      MODIFIED     
hf.co/RichardErkhov/cais_-_zephyr_7b_r2d2-gguf:Q8_0                        708b79621123    7.7 GB    2 hours ago     
zephyr-r2d2:latest                                                         7092e78591a2    4.1 GB    2 hours ago     
hf.co/RichardErkhov/cais_-_zephyr_7b_r2d2-gguf:Q4_0                        cd30e8b2afd7    4.1 GB    2 hours ago     
zephyr:7b                                                                  bbe38b81adec    4.1 GB    2 hours ago     
gemma3:12b                                                                 b92b218582c5    8.2 GB    17 hours ago    
qwen3:32b                                                                  030ee887880f    20 GB     18 hours ago    
qwen2.5:7b-instruct                                                        845dbda0ea48    4.7 GB    18 hours ago    
granite3.3:8b                                                              fd429f23b909    4.9 GB    6 days ago      
exaone3.5:7.8b                                                             c7c4e3d1ca22    4.8 GB    6 days ago      
phi4-mini:latest                                                           78fad5d182a7    2.5 GB    7 days ago      
llama3.2:3b                                                                a80c4f17acd5    2.0 GB    7 days ago      
cb-llama3:8b-q8_0                                                          ce5d731cc475    8.5 GB    9 days ago      
hf.co/featherless-ai-quants/GraySwanAI-Llama-3-8B-Instruct-RR-GGUF:Q8_0    a114d01ccccd    8.5 GB    9 days ago      
zephyr-r2d2:7b-q8_0                                                        4c322832c617    7.7 GB    9 days ago      
hf.co/mradermacher/zephyr_7b_r2d2-GGUF:Q8_0                                3eedd26047f3    7.7 GB    9 days ago      
zephyr:7b-beta-q8_0                                                        f684109a5a8d    7.7 GB    9 days ago      
qwen2.5:7b-instruct-q8_0                                                   2d9500c94841    8.1 GB    9 days ago      
repbend-llama3:8b-q8_0                                                     025cab3dfcdf    8.5 GB    11 days ago     
hf.co/mradermacher/RepBend_Llama3_8B-GGUF:Q8_0                             25e4991a8bc0    8.5 GB    11 days ago     
repbend-mistral:7b-q8_0                                                    1822f3187ee1    7.7 GB    11 days ago     
hf.co/mradermacher/RepBend_Mistral_7B-GGUF:Q8_0                            2cea8ee103c6    7.7 GB    11 days ago     
llama3:8b-instruct-q8_0                                                    1b8e49cece7f    8.5 GB    11 days ago     
mistral:7b-instruct-v0.2-q8_0                                              3f321fd2a1c3    7.7 GB    11 days ago     
llama-guard3:8b                                                            46f211c3d866    4.9 GB    11 days ago     
qwen3.5:4b                                                                 2a654d98e6fb    3.4 GB    2 weeks ago     
gemma4:26b                                                                 08ae7ec1744b    18 GB     2 weeks ago     
qwen3.8-uncensored-cyber:27b                                               5049a80b8ff8    16 GB     3 weeks ago     
qwen3.5:9b                                                                 6488c96fa5fa    6.6 GB    4 weeks ago     
solar:10.7b                                                                059fdabbe6e6    6.1 GB    5 weeks ago     
qwen2-math:1.5b                                                            a4fdda0c6cc5    934 MB    5 weeks ago     
gemma4:e2b                                                                 7fbdbf8f5e45    7.2 GB    5 weeks ago     
gemma4:e4b                                                                 c6eb396dbd59    9.6 GB    5 weeks ago     
qwen3.8:27b                                                                22130167c4c2    17 GB     5 weeks ago
```

## hf.co/RichardErkhov/cais_-_zephyr_7b_r2d2-gguf:Q8_0

```
# FROM hf.co/RichardErkhov/cais_-_zephyr_7b_r2d2-gguf:Q8_0
FROM C:\Users\bojung\.ollama\models\blobs\sha256-6d3e460944627783e6d6d05be873801cc8fa106b3a6239002f429b80e470c418
PARAMETER stop <|system|>
PARAMETER stop <|user|>
PARAMETER stop <|assistant|>
PARAMETER stop </s>
```

템플릿:
```
<|system|>
{{ .System }}</s>
<|user|>
{{ .Prompt }}</s>
<|assistant|>
```

## zephyr-r2d2:latest

```
# FROM zephyr-r2d2:latest
FROM C:\Users\bojung\.ollama\models\blobs\sha256-623dc1e1c250c71b482ab97f029a908ac7ded6c5a7ecf67438a763c9e0855b12
PARAMETER stop <|system|>
PARAMETER stop <|user|>
PARAMETER stop <|assistant|>
PARAMETER stop </s>
```

템플릿:
```
{{- if .System }}
<|system|>
{{ .System }}
</s>
{{- end }}
<|user|>
{{ .Prompt }}
</s>
<|assistant|>
```

## hf.co/RichardErkhov/cais_-_zephyr_7b_r2d2-gguf:Q4_0

```
# FROM hf.co/RichardErkhov/cais_-_zephyr_7b_r2d2-gguf:Q4_0
FROM C:\Users\bojung\.ollama\models\blobs\sha256-623dc1e1c250c71b482ab97f029a908ac7ded6c5a7ecf67438a763c9e0855b12
PARAMETER stop <|system|>
PARAMETER stop <|user|>
PARAMETER stop <|assistant|>
PARAMETER stop </s>
```

템플릿:
```
<|system|>
{{ .System }}</s>
<|user|>
{{ .Prompt }}</s>
<|assistant|>
```

## zephyr:7b

```
# FROM zephyr:7b
FROM C:\Users\bojung\.ollama\models\blobs\sha256-730ebed2578e5be3e25c3ba155b06cb46690426682a38127cb72a9697e4443b4
PARAMETER stop <|system|>
PARAMETER stop <|user|>
PARAMETER stop <|assistant|>
PARAMETER stop </s>
```

템플릿:
```
{{- if .System }}
<|system|>
{{ .System }}
</s>
{{- end }}
<|user|>
{{ .Prompt }}
</s>
<|assistant|>
```

## zephyr-r2d2:7b-q8_0

```
# FROM zephyr-r2d2:7b-q8_0
FROM C:\Users\bojung\.ollama\models\blobs\sha256-5dff12d79658558d731bee34dc34d60e616ea6355d37cbf4a3c956f82ef3fb8c
PARAMETER stop <|system|>
PARAMETER stop <|user|>
PARAMETER stop <|assistant|>
PARAMETER stop </s>
```

템플릿:
```
{{- if .System }}
<|system|>
{{ .System }}
</s>
{{- end }}
<|user|>
{{ .Prompt }}
</s>
<|assistant|>
```

## hf.co/mradermacher/zephyr_7b_r2d2-GGUF:Q8_0

```
# FROM hf.co/mradermacher/zephyr_7b_r2d2-GGUF:Q8_0
FROM C:\Users\bojung\.ollama\models\blobs\sha256-5dff12d79658558d731bee34dc34d60e616ea6355d37cbf4a3c956f82ef3fb8c
PARAMETER stop <|system|>
PARAMETER stop <|user|>
PARAMETER stop <|assistant|>
PARAMETER stop </s>
```

템플릿:
```
<|system|>
{{ .System }}</s>
<|user|>
{{ .Prompt }}</s>
<|assistant|>
```

## zephyr:7b-beta-q8_0

```
# FROM zephyr:7b-beta-q8_0
FROM C:\Users\bojung\.ollama\models\blobs\sha256-8b58b66a7e4abc9ba548535d62b84d0f7c8bf222438566b8d4b9590897d125c4
PARAMETER stop <|system|>
PARAMETER stop <|user|>
PARAMETER stop <|assistant|>
PARAMETER stop </s>
```

템플릿:
```
{{- if .System }}
<|system|>
{{ .System }}
</s>
{{- end }}
<|user|>
{{ .Prompt }}
</s>
<|assistant|>
```

