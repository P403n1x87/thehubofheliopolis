Title:    An Overview of Monads in Haskell
Authors:  Gabriele N. Tornetta
Date:     2020-09-17 16:18:00 +0100
Category: Programming
Tags:     haskell, category theory, functional programming
art:      leibniz.png
pic:      haskell-monads
Summary:  Monads are arguably one of the most important concepts in functional programming. In this post we pave the street to understanding how this purely category theoretical object finds its place in a language like Haskell.


[TOC]


# Introduction

If you are learning a functional programming language like Haskell, sooner or
later you will find yourself dealing with the concept of **monad**. You probably
knew already that there is a fair bit of category theory embedded in the
language, and this comes as no surprise at all. Indeed, functional programming
languages were developed with the goal of making lambda calculus practical and,
as it turns out, type theory has many relations to category theory.

In this post we make our way to the concept of monads in Haskell starting from
the notion of functor. The ultimate goal is to motivate the use of the term
monad by showing that we indeed have a monadic structure, but also give a
somewhat rigurous justification of the fact that "all told, monads are just
monoids in the category of endofunctors".


# Functors

A typical pattern of functional programming is that of applying a function to a
list element-wise. There are many ways of doing this, but the most general one
is that of using the `map` function

	:::haskell
	map :: (a -> b) -> [a] -> [b]

That is, `map` takes a function `a -> b` and a list of type `[a]` to produce a
list of type `[b]` by simply applying the function to each entry of the first
list. Two important properties of the function `map` follow from this
definition. The first involves its interaction with the identity function `id ::
a -> a` which simply evaluates to its sole argument. Indeed,

	:::haskell
	map id = id

in the sense that both sides represent the same function. Now, if we have two
functions, `f :: a -> b` and `g :: b -> c`, it doesn't matter whether we first
compute the composition `g . f` and apply it to `map`, or compose `map g` with
`map f`. The net result is that we obtain a function that takes a list of type
`[a]` that is sent to a list of type `[c]` whose elements are precisely given by
the image of each element of the initial list through the composition `g . f`.
We can express this fact with the identity

	:::haskell
	map (f . g) = map f . map g

Let's look back at what we have here. In more abstract terms, we can think of
the operation of putting square brackets around a type as some sort of map on
the set of Haskell types into itself, namely $[\ \cdot\ ] : a \mapsto [a]$, for
any Haskell type $a$. Observe further that the type of the function `map` is
indeed `map :: (a -> b) -> ([a] -> [b])`. That is to say that `map` sends a
function `a -> b` to a function `[a] -> [b]`, together with the two properties
above.

We may be tempted, at this point, to introduce the Haskell category
$\mathsf{Hask}$, whose objects are the Haskell types, and whose arrows are the
Haskell functions, i.e. those types that can be put into the form `a -> b` for
some Haskell types `a` and `b`. If we do so, we then recognise that the pair
(`[]`, `map`) defines a functor from $\mathsf{Hask}$ into itself. That's because
`[]` maps objects to objects (lists) and `map` maps functions to functions
(between lists). That these mappings are functorial follows immediately from the
two properties that we have observed earlier.

The next abstraction step is in realising that there is nothing special in the
(`[]`, `map`) pair. For if all we want are endofunctors on $\mathsf{Hask}$, all
we really need is a _parametrised_ type `T` and a map `fmap :: (a -> b) -> T a
-> T b` that _plays nicely_ with `T`, in the sense that it satisfies the
functoriality properties

	:::haskell
	fmap id = id

and

	:::haskell
	fmap (f . g) = fmap f . fmap g

for any functions `f` and `g`. We then see that the list example we have
analyised above is just the special case where `T a = [a]` and `fmap = map`.

To get a feel of what functors mean in Haskell (or more generally in functional
programming), we should regard the parametrised type `T` as a sort of
_container_ type. A list, of course, is an example of a container, as it
contains multiple instances of a certan type in an ordered fashon. But `T` can
also be, e.g., a rooted tree with values of type `a` on each of its nodes. So,
generally, `T` is some sort of container structure that accomodates for multiple
values of the parameter type `a`.

Notice now how the definition of `fmap` depends on the parametrised type `T`.
This means that the first step in defining an endofunctor over $\mathsf{Hask}$
is to produce one such parametrised type `T`. But once we have one, can we find
an `fmap` such that (`T`, `fmap`) is a functor? The answer to this question very
much depends on the nature of `T`, but what we can be certain of is that once we
have found one such `fmap`, then it is **unique**. Why? This is a consequence of
the so-called `parametricity` result, which derives from parametric
polymorphism. The function `fmap :: (a -> b) -> T a -> T b` implies universal
quantifiers for the types `a` and `b`. That is to say, for any types `a` and
`b`, `fmap` sends a function `a -> b` to a function `T a -> T b`. The key
observation is that, because of this parametric dependency on the types `a` and
`b`, the function `fmap` cannot act in a way that depends on a particular choice
of the types, but can depend at most on the container structure described by the
parametrised type `T`.

In order to understand this concept, let's take a step back and consider again
the special case of lists. Suppose that we have another candidate `fmap'` for an
`fmap` other than `map`. Since the types are arbitrary, such new candidate can
only interact with the list structure, i.e. apply the first argument, that is,
the function `f :: a -> b` to each element of the list of type `[a]` to produce
`[b]`, and perhaps do a reshuffling. Now, if we apply this new candidate to the
identity `id :: a -> a`, we get precisely the reshuffling bit `s = fmap' id`. On
the other hand, `fmap'` must satisfy the functor properties, and in particular
`fmap' id = id`, whence `s = id`. That is to say that `fmap'` cannot actually do
any reshuffling, so it must coincide with `map`.

The general argument works in the same way, we only need to replace the list
structure with a general one `T` and argue that by the functor properties `fmap`
can only map a function to each element of type `a` inside `T a` while
preserving the container structure described by `T`.

> More elegantly, this result could have been obtained using the _free theorem_
> associated to the type `(a -> b) -> (T a -> T b)`; see [(Wadler,
> 1989)](http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.38.9875&rep=rep1&type=pdf)
> for the details.


# Applicative Functors

We have seen that functors are a generalisation of the common pattern of mapping
a function over the elements of a list. Can we generalise to mapping of
functions with more than one argument? That is to say, given that (`T`, `fmap`)
describes a functor, can we find, e.g., `fmap2 :: (a -> b -> c) -> (T a -> T b
-> T c)`, that satisfies some reasonable coherence properties? A first
observation is that the type `a -> b -> c` is identical to `a -> (b -> c)`, just
by definition. If we apply `fmap` to any instances of this type we would get
something of type `T a -> T (b -> c)`, which isn't quite what we want. _But_, if
we had a function `<*> :: T (a -> b) -> (T a -> T b)` we would get closer, but
not quite there yet. Indeed, we could now define `fmap2` like so

    :::haskell
    fmap2 :: (a -> b -> c) -> (T a -> T b -> T c)
    fmap2 f x y = <*> (fmap f x) y

that is, we curry the result of `fmap f` with the first argument `x` and then
apply `<*>` to the result to obtain a function that we can compute on `y` to get
a result of type `T c`. Of course, we can now repeat these steps to define
`fmap3 :: (a -> b -> c -> d) -> (T a -> T b -> T c -> Td)` by using `fmap2` as a
starting point, that is

    :::haskell
    fmap3 f x y z = <*> (fmap2 f x y) z

and carry on, to get a whole family of maps `fmapn`. Using infix notation for
`<*>` and assuming associativity to the left, we could then write the general
case as

    :::haskell
    fmapn :: (a1 -> ... -> an -> b) -> (T a1 -> ... -> T an -> b)
    fmapn f x1 ... xn = fmap f x1 <*> ... <*> xn

This is now starting to look just like function application, except that we are
not making that very explicit with the first argument `x1` of type `T a1`. If we
wanted to fix that, we would have to find, e.g., a function `p` such that `fmap
f x1 = (p f) <*> x`. What's the type of `p`? We see that `p :: a -> T a` would
work well here, so if we could find such a function we could push the base of
the recursion back and define `fmap` itself in terms of `p` and `<*>`. Then we
could easily generalise functors to functions of an arbitrary number of
arguments by simply mapping it through `p` and applying arguments with `<*>`.

In Haskell, it is customary to call the function `p` with the name `pure`; any
functor for which one can define both `pure` and `<*>` is then called an
_applicative_ functor. The importance of these special objects does not come
solely from the fact that they generalise the notion of mapping to functions of
more than one argument. Indeed, they represent an important step toward
_effectful_ programming inside a purely functional programming language. Perhaps
we can appreciate this better with a concrete example based on the functor
`Maybe`. Its values can be used to represent the success or failure of an
operation. For exmaple, when an operation failed, we can simply return
`Nothing`, else we return `Just x`, where `x` is the valid result of the
operation. Haskell makes `Maybe` into an applicative functor by default by
defining

    :::haskell
    pure = Just

    Nothing <*> _ = Nothing
    (Just f) <*> mx = fmap f mx

We see from the above definitions and the recursive nature of applicative
functors that the propagation of the occurrence of an invalid value like
`Nothing` during the computation is automatically propagated to the end result,
with no need to put checks in place for each argument of the function `f`.

Before moving on, we should spend some more time looking back at the identity
`(pure f) <*> x = fmap f x` and recalling that `fmap` must satisfy some
coherence properties that make it part of the description of a functor. As we
have said earlier, we expect `pure` and `<*>` to satisfy some coherence
properties themselves if they are to work as they are supposed to, and we see
why that is. One of such properties comes for free, viz.

    :::haskell
    (pure id) <*> x = x

since `fmap id x = x`. The other properties that are required of `pure` and
`<*>` are

    :::haskell
    pure (f x) = pure f <*> pure x
    x <*> pure y = pure ($ y) <*> x
    pure (.) <*> x <*> y <*> z = x <*> (y <*> z)

and all ensure that `pure` pretty much delivers what it promises. For example,
the first of the above three properties is just a way of ensuring that `pure`
embeds ordinary function application into the effectful programming realm in an
unsurprising way.

> Deeper ties with Category Theory are presented in details in the original
> paper [(McBride & Paterson,
> 2008)](http://www.staff.city.ac.uk/~ross/papers/Applicative.html). There it is
> shown how one can give a symmetric definition of `<*>` and show that an
> applicative functor is just a _lax monoidal functor_.


# Monads
 
Monads have been introduced to crystallise yet another common pattern in
effectful programming that is not quite captured by both the Functor and the
Applicative "patterns".

Consider the case of a program that consists of a series of steps that need to
be executed in order, and such that the output of one is used as input for the
next one. A classical example is a function `f` that requires the result of a
division `g x y = x / y`. It is clear that if `g` receives a `0` as second
argument during the execution of the program, we are in an exceptional situation
that somehow we need to handle. But we can hardly do so if `g` is of type, say,
`g :: Int -> Int -> Int`. Lacking support for catching and reacting to
exceptions, we need a way to _signal_ that something went wrong and propagate
that to the end.

The first obvious thing to do is to rewrite `g` in such a way that its type is
`g :: Int -> Int -> Maybe Int`, so that `g _ 0 = Nothing` and `g x y = Just (x /
y)`. Then, for every function `f` that receives the output of `g` as input, we
would have to go through the tedious process of checking whether the value it
received is valid or not. If those functions have been coded already, then we
have a problem that is not much fun to solve.

How about we check the arguments we are passing to a function that is coming
from another function, detecting any failures to propagate, else continue with
the normal execution? With this approach, all we need is a _binding_ function
`>>= :: Maybe a -> (a -> Maybe b) -> Maybe b` that checks the first argument,
and only apply it to the second argument if it makes sense to do so, propagating
any "bad" value otherwise. It is clear, just by looking at the involved types,
that applicative functors are of no much use in this case, since a function like
`g` is not _pure_, given that it can produce a side effect like `Nothing`.
Hence, what we have here is a different pattern: the **monad** pattern.

The notion of _monad_ comes from category theory and arises from adjunction. But
before we can make contact with the Haskell notion of monads that was given
above we need to replace the bind operator `>>= :: M a -> (a -> M b) -> M b`
(here `M` is a parametrised type that we want to turn into a monad; hence `M` is
a functor) with the function `join :: M (Μ a) -> M a`. Together with `pure` (or
`return` we should say), it provides the structure that makes the endofunctor
`M` a monad. In a nutshell, what we want to do is prove that `(M, pure, join)`
has the monad structure. And we shall also see in what sense a monad can be
defined as a "monoid in the category of endofunctors", as Mac Lane put it.

First things first, let's see how the `join` function relates to the bind
operator `>>=`. You can convince yourself that the definition

    :::haskell
    join x = x >>= id

has the correct type. As to what this is good for from a practical point of
view, recall the example of the function `g :: Int -> Int -> Maybe Int` that we
saw before. We argued that we couldn't apply the applicative pattern because `g`
is not a pure function and that the issue boiled down to `g` having the "wrong"
type. For if we used `fmap2 :: (a -> b -> c) -> (Maybe a -> Maybe b -> Maybe
c)`, we would end up with `fmap2 g :: Maybe Int -> Maybe Int -> Maybe (Maybe
Int)`. But now, if we curry and apply `join` we can _cure_ that double boxing
`Maybe (Maybe Int)` to get back a `Maybe Int` instead.

Let's now look at the coherence properties that must be satisfied by `join`. The
first one we note is its interaction with itself

    :::haskell
    join . (fmap join) = join . join

which is quite easily understood if we look at the case of lists. Here the
`join` function does what we would expect, considering its name: it flattens the
list of lists `[[a]]` into a single list `[a]` obtained by concatenation. The
second coherence property that we look at involves the interaction between
`join` and `pure` (or `return`), viz.

    :::haskell
    join . pure = join . (fmap pure) = id

which can be understood as saying that when we embed a value of type `M a` into
the "pure" part of `M (M a)`, then `join` "unboxes" the structure and gives us
the initial value back.

Now, thanks to the two above properties, we can easily recognise a monad
structure for the triplet `(M, pure, join)`, with `T` the endofunctor and `pure`
and `join` representing the required natural transformations.

In what sense can we regard a monad as a monoid? The general qualitative answer
is that the map `pure` is akin to a unit and `join` is akin to the binary
operation on a monoid. But if we look at the type of `join`, which is `M (M a)
-> M a`, we don't see any sign of a Cartesian product. Instead, we have some
sort of composition of functors, whence the second part of the qualitative
answer, i.e. that the Cartesian product should be replaced with "composition".
But what kind of composition? Let's clarify these points a bit.

Let'sabandon Haskell functors for now, since it is pretty clear that the last
"pattern" that we have described has all the rights to be called a _monad_, and
look at the matter from the perspective of category theory. Given functors $F, G
: C \to D$, $J, K : D \to E$ and natural transformations $\alpha : F \Rightarrow
G$ and $\beta : J \Rightarrow K$, we can construct a new natural transformation
$\beta \circ \alpha$ between the functors $J \circ F$ and $K \circ G$ according
to the following commutative diagram

$$\require{AMScd}
\begin{CD}
  F(X) @>\alpha_X>> G(X)\\
  @VJVV @VJVV\\ (J\circ F)(X) @>J(\alpha_X)>>
(J\circ G)(X) @>\beta_{G(X)}>> (K\circ G)(X)
\end{CD}$$

That is, we define the natural transformation $\beta\circ\alpha : J \circ F
\Rightarrow K \circ G$ as having components

$$(\beta \circ \alpha)_X = \beta_{G(X)} \circ J(\alpha_X)$$

Using $\eta$ and $\mu$ as short-hand notation for the natural transformations
`pure` and `join`, we see that the two coherence properties above can be stated
in the form of commutative diagram

$$\require{AMScd}
\begin{CD}
  M \circ M \circ M @>\iota_M\circ \mu>> M \circ M\\
  @V\mu \circ \iota_MVV @V\mu VV\\
  M \circ M @>\mu>> M
\end{CD}$$

and

$$\require{AMScd}
\begin{CD}
  M \circ I @> \iota_M \circ \eta >> M \circ M @< \eta\circ\iota_M << I \circ
    M\\
  @| @V \mu VV @|\\
  M @= M @= M
\end{CD}$$

where $\iota_M$ denotes of course the identity natural transformation. Note
that, in terms of components, the two diagrams are equivalent to the relations

$$\forall X,\ \mu_X(M(\mu_X)) = \mu_X(\mu_{M(X)})$$

and

$$\forall X,\ \mu(M(\eta_X)) = \mu(\eta_{M(X)}),$$

which we can easily translate back into the original properties for the Haskell
`pure` and `join`.

The above diagrams should now make more precise the meaning of Mac Lane's sentence

> All told, a monad in $X$ is just a monoid in the category of endofunctors of
> $X$, with product $\times$ replaced by composition of endofunctors and unit
> set by the identity endofunctor.

Indeed we see that $\mu$ and $\eta$ have diagrams similar to the analogous
concepts in monoids, with the difference that functor composition $\circ$ is now
everywhere we would expect a Cartesian product $\times$.
