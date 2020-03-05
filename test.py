import pickle


if __name__ == "__main__":
    x = "test"
    x_pickle = pickle.dumps(x)
    x_encode = x.encode("utf-8")
    x_cat = x_pickle + x_encode
    x_bytes = bytes(x, "utf-8")

    print(x)
    print(x_pickle)
    print(x_encode)
    print(x_cat)
    print(x_bytes)

